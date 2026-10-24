import ssl
from unittest.mock import MagicMock, Mock, patch

import httpx2 as httpx
import pytest
from aurelius_atlas_fastapi_example.providers.http import HTTP_TIMEOUT, http_client
from fastapi import HTTPException


def test__http_client_verifies_with_system_trust_without_ca_file(settings_plaintext: Mock) -> None:
    """Without a configured CA bundle the client verifies through the system trust."""
    with patch("aurelius_atlas_fastapi_example.providers.http.httpx.Client") as client_class:
        generator = http_client(settings_plaintext)
        next(generator)
        generator.close()

    _, kwargs = client_class.call_args
    assert isinstance(kwargs["verify"], ssl.SSLContext)
    assert kwargs["timeout"] == HTTP_TIMEOUT


def test__http_client_verifies_with_configured_ca_file(settings_http_ca: Mock) -> None:
    """A configured CA bundle roots the client's TLS context (DD-122)."""
    with (
        patch("aurelius_atlas_fastapi_example.providers.http.httpx.Client") as client_class,
        patch("aurelius_atlas_fastapi_example.providers.http.ssl.create_default_context") as make_context,
    ):
        generator = http_client(settings_http_ca)
        next(generator)
        generator.close()

    _, kwargs = client_class.call_args
    make_context.assert_called_once_with(cafile="/certs/ca.pem")
    assert kwargs["verify"] is make_context.return_value


def test__http_client_raises_service_unavailable_on_http_error(settings_plaintext: Mock) -> None:
    """Upstream HTTP errors are translated into a 503 service unavailable."""
    generator = http_client(settings_plaintext)
    generator.send(None)

    with pytest.raises(HTTPException) as exc_info:
        generator.throw(httpx.ConnectError("boom"))

    assert exc_info.value.status_code == 503


def test__http_client_yields_client_from_context_manager(settings_plaintext: Mock) -> None:
    """The client yielded to consumers is the one created by the provider."""
    expected = MagicMock()

    with patch("aurelius_atlas_fastapi_example.providers.http.httpx.Client") as client_class:
        client_class.return_value.__enter__.return_value = expected

        generator = http_client(settings_plaintext)
        actual = next(generator)
        generator.close()

    assert actual is expected
