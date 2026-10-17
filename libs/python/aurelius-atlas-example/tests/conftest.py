import secrets
from collections.abc import Generator

import psycopg
import pytest
from aurelius_atlas_example import Entity
from aurelius_atlas_sdk.testing.tls import (
    TLS_POSTGRES_HOST,
    TLS_POSTGRES_IMAGE,
    TlsCertificates,
    configure_tls_postgres,
    tls_certificates,
)
from sqlalchemy import URL, Connection, Engine, create_engine
from sqlmodel import Session, SQLModel, delete
from testcontainers.community.postgres import PostgresContainer


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
def db_url(db_container: PostgresContainer, db_tls_material: TlsCertificates) -> URL:
    """Return a SQLAlchemy URL for connecting to the test PostgreSQL container."""
    return URL.create(
        drivername="postgresql+psycopg",
        username=db_container.username,
        password=db_container.password,
        # TLS_POSTGRES_HOST, not get_container_host_ip(): the ephemeral certificate
        # only covers loopback names and libpq verifies the host against them.
        host=TLS_POSTGRES_HOST,
        port=db_container.get_exposed_port(5432),
        database=db_container.dbname,
        query={
            # The container enforces TLS (hostssl-only pg_hba) with an ephemeral
            # trustme CA, matching dev/e2e: verify the server against that CA.
            "sslmode": "verify-full",
            "sslrootcert": str(db_tls_material.ca_bundle_path),
        },
    )


@pytest.fixture()
def db_engine(db_url: URL) -> Generator[Engine]:
    """Create the SQLModel schema in the test PostgreSQL database."""
    engine = create_engine(db_url)

    SQLModel.metadata.create_all(engine)

    yield engine

    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_connection(db_engine: Engine) -> Generator[Connection]:
    """Provide a database connection for each test."""
    with db_engine.connect() as connection:
        yield connection


@pytest.fixture()
def db_connection_cdc(db_url: URL, db_engine: Engine) -> Generator[psycopg.Connection]:
    """Provide a database connection for each test."""
    del db_engine

    connection = psycopg.connect(
        autocommit=True,
        host=db_url.host,
        port=db_url.port,
        dbname=db_url.database,
        user=db_url.username,
        password=db_url.password,
        sslmode="verify-full",
        sslrootcert=str(db_url.query["sslrootcert"]),
    )

    yield connection

    connection.close()


@pytest.fixture()
def db_session(db_engine: Engine) -> Generator[Session]:
    """Provide a clean SQLModel session for each test."""
    with Session(db_engine, expire_on_commit=False) as session:
        yield session

    with Session(db_engine) as cleanup_session:
        cleanup_session.exec(delete(Entity))
        cleanup_session.commit()


@pytest.fixture()
def entity(db_session: Session) -> Generator[Entity]:
    """Create and return a single test entity."""
    entity = Entity(name="Test Entity", description="A test entity")

    db_session.add(entity)
    db_session.commit()

    db_session.refresh(entity)

    yield entity

    db_session.delete(entity)
    db_session.commit()
