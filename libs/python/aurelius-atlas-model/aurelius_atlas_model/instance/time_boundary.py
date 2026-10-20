"""``TimeBoundary``: one validity period of a classification (ENT-13)."""

from aurelius_atlas_model.base import AtlasModel

TIME_FORMAT = "yyyy/MM/dd HH:mm:ss"
"""The Java date format of ``startTime`` and ``endTime`` (``TimeBoundary.TIME_FORMAT``); checked in 2.1b."""


class TimeBoundary(AtlasModel):
    """A period in which a classification applies; the times are strings in ``TIME_FORMAT``.

    ``timeZone`` is a Java time zone id, or null for the server's local time.
    """

    start_time: str | None = None
    end_time: str | None = None
    time_zone: str | None = None
