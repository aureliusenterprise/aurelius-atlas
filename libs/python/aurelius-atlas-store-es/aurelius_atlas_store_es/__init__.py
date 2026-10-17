from .errors import StoreError, StoreUnavailableError, UnsupportedVersionError
from .health import HealthReport, HealthStatus, check_health
from .settings import StoreSettings
from .store import SUPPORTED_MAJOR_VERSION, ElasticsearchStore

__all__ = [
    "SUPPORTED_MAJOR_VERSION",
    "ElasticsearchStore",
    "HealthReport",
    "HealthStatus",
    "StoreError",
    "StoreSettings",
    "StoreUnavailableError",
    "UnsupportedVersionError",
    "check_health",
]
