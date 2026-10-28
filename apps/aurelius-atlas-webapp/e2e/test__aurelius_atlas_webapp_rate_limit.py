"""E2E: the browser rate limit at the nginx edge (9.3, SRV-09, DD-238).

The e2e nginx config (``config/nginx.conf``) puts a leaky bucket on the
``/api/`` proxy — key ``$binary_remote_addr``, deliberately test-sized
(``rate=60r/m``, ``burst=20``) so a sequential loop can outspend it; the
shipped 300r/m + burst 100 is browser-sized and unprovable at suite speed.
Every request in this suite arrives from the Docker bridge gateway, so all
share one bucket — that is the point: a browser floods, gets 429, the app
sees one refused call and the alert drawer (ALR-05) is its UX for it.

The test drains the bucket before returning (full refill = burst/rate = 20s):
the file sorts after the main suite and before the resilience file, and the
resilience scenarios ride ``/api/`` too — a drained bucket keeps them clean.
The refusal shape is nginx's own (429, an HTML body): the server never rate
limits (DD-238), so no Atlas error body rides a 429, and nginx sends no
Retry-After.
"""

import time
from urllib.parse import urljoin

from playwright.sync_api import Page

BURST = 120
"""Requests fired at the bucket: burst 20 + 1 token/s over the ~10s the loop takes."""

DRAIN_SECONDS = 25
"""Full refill at burst=20, rate=60r/m is 20s; 25s with margin."""


def test__the_edge_bucket_serves_a_burst_then_refuses_429(page: Page, root_url: str) -> None:
    """The first burst passes, the flood past it is refused 429, and a drained bucket serves again (SRV-09)."""
    version = urljoin(root_url, "/api/atlas/admin/version")
    statuses: list[int] = []
    for _ in range(BURST):
        response = page.request.get(version, ignore_https_errors=True, timeout=10_000)
        statuses.append(response.status)

    assert statuses[0] == 200  # the bucket starts full
    refused = [status for status in statuses if status == 429]
    assert refused, f"no 429 in {BURST} requests: {set(statuses)}"

    time.sleep(DRAIN_SECONDS)
    after = page.request.get(version, ignore_https_errors=True)

    assert after.status == 200  # the refill returns the client, unbanned (leaky bucket, not a blocklist)
