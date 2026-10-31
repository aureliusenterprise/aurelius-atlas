"""The login and logout pages: a browser's sign-in at the identity provider, and its sign-out (AUT-05, AUT-07).

Where Atlas's Keycloak adapter signs a browser in (``login.jsp``) and out (``logout.html``).
"""

from fastapi import APIRouter, Request, Response
from fastapi.responses import PlainTextResponse, RedirectResponse

from aurelius_atlas_server.authentication import (
    LOGIN_PATH,
    SESSION_COOKIE,
    Login,
    SessionStore,
    set_session_cookie,
)
from aurelius_atlas_server.oidc_client import OidcClient, SignInError

LOGIN = APIRouter(tags=["Login"])

SIGN_IN_FAILED = "Sign-in failed"


@LOGIN.get(LOGIN_PATH)
async def login(request: Request) -> Response:
    """Start a sign-in at the provider, or finish one on its return to the page first asked (AUT-05)."""
    sessions: SessionStore = request.app.state.sessions
    oidc: OidcClient = request.app.state.oidc
    redirect_uri = f"{request.base_url}{LOGIN_PATH.lstrip('/')}"
    session = sessions.get(request.cookies.get(SESSION_COOKIE))
    params = request.query_params
    if "code" in params or "error" in params:
        login_state = None if session is None else session.login
        if session is None or login_state is None or params.get("state") != login_state.state or "error" in params:
            return PlainTextResponse(SIGN_IN_FAILED, status_code=401)
        try:
            await oidc.sign_in(session, login_state, params["code"], redirect_uri)
        except SignInError:
            return PlainTextResponse(SIGN_IN_FAILED, status_code=401)
        session = sessions.renew(session)
        target, session.return_to = _local(session.return_to), None
        response = RedirectResponse(target, status_code=302)
        set_session_cookie(response, session)
        return response
    session = session if session is not None else sessions.create()
    session.login = Login()
    response = RedirectResponse(await oidc.authorization_url(session.login, redirect_uri), status_code=302)
    set_session_cookie(response, session)
    return response


@LOGIN.get("/logout.html")
async def logout(request: Request) -> Response:
    """End the session and sign out at the provider, back to the dashboards (AUT-07)."""
    sessions: SessionStore = request.app.state.sessions
    oidc: OidcClient = request.app.state.oidc
    session = sessions.get(request.cookies.get(SESSION_COOKIE))
    id_token = None if session is None else session.id_token
    if session is not None:
        sessions.remove(session.id)
    response = RedirectResponse(await oidc.end_session_url(id_token, str(request.base_url)), status_code=302)
    response.delete_cookie(SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="lax")
    return response


def _local(path: str | None) -> str:
    """A page of this server to return to: its own path, else ``/``; never another site."""
    if path is None or not path.startswith("/") or path.startswith("//") or "\\" in path:
        return "/"
    return path
