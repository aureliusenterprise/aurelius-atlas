"""The fenced /etc/hosts block for browser legs (CHT-106).

Python suites never need this — the resolver shim covers them — but Playwright
browsers and ``page.request`` resolve outside the process, so ``install.sh
hosts`` maintains a fenced block mapping the edge hostnames to the live
Gateway address. The block is the script's own: re-runs replace it wholesale
and touch nothing outside the fence.
"""

import socket

BEGIN = "# BEGIN aurelius-atlas-cluster"
END = "# END aurelius-atlas-cluster"
"""The fence markers — everything between them belongs to this tool."""

_SHADOW_ERROR = "the hosts block must not shadow the machine's own hostname {!r}: {}"


def hosts_block(text: str, entries: dict[str, str], *, hostname: str | None = None) -> str:
    """Return ``text`` with the fenced block rewritten to ``entries`` (hostname -> address).

    First insert appends the block; a re-run replaces it in place (converging
    on the current Gateway IP after churn) and leaves every other line —
    including a machine's own hostname line — untouched. An empty ``entries``
    removes the block entirely (a cluster going down should not strand hosts).

    Refuses to write when ``entries`` would shadow the machine's own
    ``hostname`` — on minikube the Gateway IP answers on the node, whose
    /etc/hosts must keep resolving its real name, and deleting that line
    breaks cluster DNS resolution for every lookup that falls through.
    """
    if hostname is None:
        hostname = socket.gethostname()
    shadowed = sorted(name for name in entries if name.split(":")[0] == hostname)
    if shadowed:
        raise ValueError(_SHADOW_ERROR.format(hostname, shadowed))

    lines = text.splitlines()
    kept: list[str] = []
    inside = False
    for line in lines:
        if line.strip() == BEGIN:
            inside = True
            continue
        if line.strip() == END:
            inside = False
            continue
        if not inside:
            kept.append(line)

    if entries:
        block = [BEGIN]
        block += [f"{address} {name}" for name, address in sorted(entries.items())]
        block.append(END)
        while kept and not kept[-1].strip():
            kept.pop()
        kept += ["", *block]

    result = "\n".join(kept)
    return result + "\n" if result else ""
