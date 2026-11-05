"""``python -m aurelius_atlas_server.snapshots``: list, take or restore the store's snapshots (SNP-04, SNP-05).

The command reads the server's store settings from the same environment, so it runs from the server's image:
in a cluster as the chart's restore Job, by hand wherever the server's settings are set. A restore runs while no
server writes to the store.
"""

import argparse
import asyncio
import sys
from collections.abc import Callable, Sequence

from aurelius_atlas_store_es import ElasticsearchStore
from aurelius_atlas_store_es.snapshots import SnapshotError, list_snapshots, restore, take_snapshot

from aurelius_atlas_server.settings import SNAPSHOT_INDICES, StoreAccessSettings

PROG = "python -m aurelius_atlas_server.snapshots"


def parser() -> argparse.ArgumentParser:
    """The command's arguments: ``list``, ``take``, or ``restore [--snapshot NAME] [--replace]``."""
    commands = argparse.ArgumentParser(prog=PROG, description="List, take or restore the store's snapshots.")
    choices = commands.add_subparsers(dest="command", required=True)
    choices.add_parser("list", help="the repository's snapshots, oldest first")
    choices.add_parser("take", help="a snapshot now, by the policy, waiting until it has finished")
    restoring = choices.add_parser("restore", help="restore the server's indices from a snapshot")
    restoring.add_argument("--snapshot", help="the snapshot's name; by default the newest successful one")
    restoring.add_argument("--replace", action="store_true", help="delete the server's indices first")
    return commands


async def run(args: argparse.Namespace, settings: StoreAccessSettings, out: Callable[[str], None]) -> None:
    """Carry out the parsed command against the store, writing what it did to ``out``."""
    async with ElasticsearchStore(settings.store_settings()) as store:
        if args.command == "list":
            for snapshot in await list_snapshots(store.client):
                out(f"{snapshot.name}\t{snapshot.state}\t{snapshot.started.isoformat()}\t{len(snapshot.indices)}")
        elif args.command == "take":
            out(await take_snapshot(store.client))
        else:
            result = await restore(
                store.client,
                indices=SNAPSHOT_INDICES,
                location=settings.snapshot_location,
                snapshot=args.snapshot,
                replace=args.replace,
            )
            out(
                f"Restored {result.snapshot}: {len(result.restored)} indices in {result.seconds:.1f} s"
                f" ({len(result.deleted)} deleted first)"
            )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command; 0 when it completed, 1 when a snapshot or restore did not (SNP-04, SNP-05)."""
    args = parser().parse_args(argv)
    settings = StoreAccessSettings()  # pyright: ignore[reportCallIssue] - read from the environment
    try:
        asyncio.run(run(args, settings, print))
    except SnapshotError as error:
        print(f"{PROG}: {error}", file=sys.stderr)  # noqa: T201 - the command's error output
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
