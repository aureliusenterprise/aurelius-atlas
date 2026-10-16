"""
Testing utilities for Aurelius applications.

Install the ``testing`` extra to use the submodules:

- :mod:`aurelius_sdk.testing.tls` — ephemeral TLS material and TLS-enforcing
  PostgreSQL container configuration.
- :mod:`aurelius_sdk.testing.testcontainers` — Docker Compose helpers.
"""

from aurelius_sdk.testing.testcontainers import capture_docker_compose_logs

__all__ = ["capture_docker_compose_logs"]
