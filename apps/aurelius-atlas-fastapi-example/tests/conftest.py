import secrets
from collections.abc import Callable, Generator
from typing import Any
from unittest.mock import Mock

import pytest
from aurelius_atlas_example import Entity
from aurelius_atlas_fastapi_example.models import Settings
from aurelius_atlas_sdk.testing.tls import (
    TLS_POSTGRES_HOST,
    TLS_POSTGRES_IMAGE,
    TlsCertificates,
    configure_tls_postgres,
    tls_certificates,
)
from pydantic import HttpUrl, SecretStr, TypeAdapter
from sqlalchemy import Engine, create_engine
from sqlmodel import Session, SQLModel, delete
from testcontainers.community.postgres import PostgresContainer


def _make_settings(**overrides: Any) -> Mock:  # noqa: ANN401
    """Return a spec'd Settings mock for a scenario, defaulted to plaintext HTTP.

    Mocks never read the environment, so tests are deterministic whatever the
    developer's or CI's ambient configuration says (Nx injects the project `.env`
    into every task's environment). `spec=Settings` keeps the mock honest: an
    attribute the model does not have — or one a future Settings field the
    scenario has not pinned yet — raises AttributeError instead of silently
    returning a truthy child mock. Every current field is pinned explicitly
    (defaults mirrored from the model) so a scenario is fully self-contained.
    """
    scenario: dict[str, Any] = {
        "auth_audience": "aurelius",
        "auth_ca_file": "",
        "auth_client_id": None,
        "auth_fail_max": 5,
        "auth_realm_name": "test-realm",
        "auth_reset_timeout": 60,
        "auth_server_url": TypeAdapter(HttpUrl).validate_python("http://localhost:8080"),
        "auto_create_schema": False,
        "cdc_disconnect_poll_timeout": 5.0,
        "cdc_shutdown_join_timeout": 2.0,
        "cdc_subscriber_queue_maxsize": 1000,
        "db_fail_max": 5,
        "db_reset_timeout": 60,
        "database_driver": "postgresql+psycopg",
        "database_host": "localhost",
        "database_name": "postgres",
        "database_password": SecretStr("test-password"),
        "database_port": 5432,
        "database_sslmode": "prefer",
        "database_sslrootcert": "",
        "database_username": "postgres",
        "environment": "production",
        "host": "127.0.0.1",
        "is_development": False,
        "log_level": "info",
        "port": 8000,
        "tls_cert_file": "",
        "tls_key_file": "",
    }
    scenario.update(overrides)
    return Mock(spec=Settings, **scenario)


@pytest.fixture
def settings_scenario() -> Callable[..., Mock]:
    """Return the scenario factory for settings combinations without a named fixture."""
    return _make_settings


@pytest.fixture
def settings_plaintext() -> Mock:
    """No TLS material anywhere: plaintext server, system-trust outbound."""
    return _make_settings()


@pytest.fixture
def settings_server_tls() -> Mock:
    """The server itself terminates TLS from a certificate and key."""
    return _make_settings(tls_cert_file="/certs/server.pem", tls_key_file="/certs/server-key.pem")


@pytest.fixture
def settings_http_ca() -> Mock:
    """Outbound HTTP verifies the auth server against a configured CA bundle."""
    return _make_settings(auth_ca_file="/certs/ca.pem")


@pytest.fixture(scope="session")
def db_credentials() -> dict[str, str]:
    """Return generated PostgreSQL credentials for the test container."""
    return {
        "database_name": "postgres",
        "database_username": "postgres",
        "database_password": secrets.token_urlsafe(16),
    }


@pytest.fixture(scope="session")
def db_tls_material() -> Generator[TlsCertificates]:
    """Generate ephemeral TLS material, removed again at session teardown."""
    with tls_certificates() as certs:
        yield certs


@pytest.fixture(scope="session")
def db_container(db_credentials: dict[str, str], db_tls_material: TlsCertificates) -> Generator[PostgresContainer]:
    """Start a real TLS-enforcing PostgreSQL container for tests."""
    container = PostgresContainer(
        TLS_POSTGRES_IMAGE,
        username=db_credentials["database_username"],
        password=db_credentials["database_password"],
        dbname=db_credentials["database_name"],
    )
    configure_tls_postgres(container, db_tls_material)
    with container:
        yield container


@pytest.fixture(scope="session")
def db_settings(
    db_container: PostgresContainer, db_tls_material: TlsCertificates, db_credentials: dict[str, str]
) -> Settings:
    """Return application settings pointed at the test PostgreSQL container.

    Real (not a mock): the engine is built from the computed database_url and
    tests model_copy() it. Every field the project `.env` could inject (Nx puts
    it in the task environment) is therefore passed explicitly, so the fixture
    is deterministic regardless of ambient configuration.
    """
    return Settings(
        # Values the tests do not exercise are pinned to the model defaults so
        # ambient environment variables can never seep into the scenario.
        auth_audience="aurelius",
        auth_ca_file="",
        auth_client_id=None,
        auth_fail_max=5,
        auth_realm_name="test-realm",
        auth_reset_timeout=60,
        auth_server_url=TypeAdapter(HttpUrl).validate_python("http://localhost:8080"),
        # Same value the default_factory computes from environment=development;
        # pinned so ambient env cannot flip it.
        auto_create_schema=True,
        cdc_disconnect_poll_timeout=5.0,
        cdc_shutdown_join_timeout=2.0,
        cdc_subscriber_queue_maxsize=1000,
        db_fail_max=5,
        db_reset_timeout=60,
        database_driver="postgresql+psycopg",
        # TLS_POSTGRES_HOST, not get_container_host_ip(): the ephemeral certificate
        # only covers loopback names and libpq verifies the host against them.
        database_host=TLS_POSTGRES_HOST,
        database_name=db_credentials["database_name"],
        database_password=SecretStr(db_credentials["database_password"]),
        # The test container enforces TLS (hostssl-only pg_hba) with an ephemeral
        # trustme CA, matching dev/e2e: verify the server against that CA.
        database_sslmode="verify-full",
        database_sslrootcert=str(db_tls_material.ca_bundle_path),
        database_port=int(db_container.get_exposed_port(5432)),
        database_username=db_credentials["database_username"],
        environment="development",
        host="127.0.0.1",
        log_level="info",
        port=8000,
        tls_cert_file="",
        tls_key_file="",
    )


@pytest.fixture(scope="session")
def db_engine(db_settings: Settings) -> Generator[Engine]:
    """Create the SQLModel schema in the test PostgreSQL database."""
    engine = create_engine(db_settings.database_url)

    SQLModel.metadata.create_all(engine)

    yield engine

    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Generator[Session]:
    """Provide a clean SQLModel session for each test."""
    with Session(db_engine, expire_on_commit=False) as session:
        yield session

    with Session(db_engine) as cleanup_session:
        cleanup_session.exec(delete(Entity))
        cleanup_session.commit()
