"""``OidcClient``: the server's confidential client at the identity provider (AUT-05 to AUT-07).

The authorization code flow with PKCE a browser signs in by, the refresh of a session's access token, and the
provider's sign-out. The provider's endpoints come from its discovery document, and every token is verified as a
bearer token is (AUT-10).
"""

import base64
import hashlib
import logging
import ssl
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx2 as httpx
from aurelius_atlas_auth import KeycloakAuth
from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool

from aurelius_atlas_server.authentication import EXPIRY_MARGIN_SECONDS, Login, Session, user_of

LOGGER = logging.getLogger("aurelius-atlas-server")

HTTP_TIMEOUT_SECONDS = 10.0


class SignInError(Exception):
    """A sign-in the provider or the checks refused."""


@dataclass(frozen=True)
class Tokens:
    """What the token endpoint answers: the access, refresh and ID tokens, and the access token's lifetime."""

    access_token: str
    expires_in: float
    refresh_token: str | None
    id_token: str | None


class OidcClient:
    """The client ``client_id`` with ``client_secret`` at the provider ``auth`` verifies tokens of.

    ``principal_claim`` and ``groups_claim`` name a user from their access token (AUT-03).
    """

    def __init__(  # noqa: PLR0913 - the client's identity and how it names users
        self,
        auth: KeycloakAuth,
        *,
        client_id: str,
        client_secret: str,
        principal_claim: str,
        groups_claim: str,
        ca_file: str | None = None,
        http: httpx.AsyncClient | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._auth = auth
        self._client_id = client_id
        self._client_secret = client_secret
        self._principal_claim = principal_claim
        self._groups_claim = groups_claim
        self._clock = clock
        context = ssl.create_default_context(cafile=ca_file) if ca_file else ssl.create_default_context()
        self._http = http if http is not None else httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS, verify=context)

    async def close(self) -> None:
        """Close the HTTP client (the application's shutdown)."""
        await self._http.aclose()

    async def authorization_url(self, login: Login, redirect_uri: str) -> str:
        """Where a browser signs in: the authorization endpoint with the client, state, nonce and PKCE (AUT-05)."""
        endpoint = (await self._discovery())["authorization_endpoint"]
        challenge = base64.urlsafe_b64encode(hashlib.sha256(login.verifier.encode()).digest()).rstrip(b"=").decode()
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self._client_id,
                "redirect_uri": redirect_uri,
                "scope": "openid",
                "state": login.state,
                "nonce": login.nonce,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
        return f"{endpoint}?{query}"

    async def sign_in(self, session: Session, login: Login, code: str, redirect_uri: str) -> None:
        """The code exchanged, the ID token's nonce checked, the session signed in as the token's user (AUT-05).

        Raises:
            SignInError: When the provider refuses the code or a token does not verify.
        """
        tokens = await self._token(
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": login.verifier,
            }
        )
        if tokens.id_token is None:
            msg = "no ID token"
            raise SignInError(msg)
        identity = await self._verify(tokens.id_token)
        if identity.get("nonce") != login.nonce:
            msg = "the ID token's nonce is not the sign-in's"
            raise SignInError(msg)
        await self._apply(session, tokens)
        session.login = None

    async def fresh(self, session: Session) -> bool:
        """Whether the session is still signed in, its access token refreshed when it expires (AUT-06).

        A refresh the provider refuses signs the session out.
        """
        if session.user is None:
            return False
        if session.access_expires - EXPIRY_MARGIN_SECONDS > self._clock():
            return True
        refreshed = None
        if session.refresh_token is not None:
            try:
                refreshed = await self._token({"grant_type": "refresh_token", "refresh_token": session.refresh_token})
                await self._apply(session, refreshed)
            except SignInError:
                refreshed = None
        if refreshed is None:
            LOGGER.info("A session's refresh failed; it is signed out")
            session.user = session.access_token = session.refresh_token = None
            return False
        return True

    async def end_session_url(self, id_token: str | None, post_logout_redirect_uri: str) -> str:
        """The provider's sign-out, back to ``post_logout_redirect_uri`` (AUT-07)."""
        endpoint = (await self._discovery())["end_session_endpoint"]
        query = {"client_id": self._client_id, "post_logout_redirect_uri": post_logout_redirect_uri}
        if id_token is not None:
            query["id_token_hint"] = id_token
        return f"{endpoint}?{urlencode(query)}"

    async def _apply(self, session: Session, tokens: Tokens) -> None:
        """The session as its tokens make it: the access token's user, its expiry, the other tokens kept."""
        claims = await self._verify(tokens.access_token)
        session.user = user_of(claims, principal_claim=self._principal_claim, groups_claim=self._groups_claim)
        session.access_token = tokens.access_token
        session.access_expires = self._clock() + tokens.expires_in
        session.refresh_token = tokens.refresh_token or session.refresh_token
        session.id_token = tokens.id_token or session.id_token

    async def _token(self, form: dict[str, str]) -> Tokens:
        """A call of the token endpoint as this client.

        Raises:
            SignInError: When the provider answers with an error or cannot be reached.
        """
        endpoint = (await self._discovery())["token_endpoint"]
        try:
            response = await self._http.post(
                endpoint, data={**form, "client_id": self._client_id, "client_secret": self._client_secret}
            )
        except httpx.HTTPError as error:
            raise SignInError(str(error)) from error
        if response.status_code != httpx.codes.OK:
            LOGGER.warning("The token endpoint refused a %s grant: %s", form["grant_type"], response.status_code)
            msg = f"the token endpoint answered {response.status_code}"
            raise SignInError(msg)
        body = response.json()
        return Tokens(
            access_token=body["access_token"],
            expires_in=float(body.get("expires_in", 0)),
            refresh_token=body.get("refresh_token"),
            id_token=body.get("id_token"),
        )

    async def _verify(self, token: str) -> dict[str, Any]:
        """The token's claims, verified as a bearer token is (AUT-02).

        Raises:
            SignInError: When the token does not verify.
        """
        try:
            return await run_in_threadpool(self._auth.verify, token)
        except HTTPException as error:
            raise SignInError(str(error.detail)) from error

    async def _discovery(self) -> dict[str, Any]:
        return await run_in_threadpool(self._auth.discovery)


__all__ = ["OidcClient", "SignInError", "Tokens"]
