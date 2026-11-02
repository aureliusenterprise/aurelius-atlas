# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved
from the
[Design Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted
entry is never edited except its status line, and a changed decision is a new
entry that supersedes the old one.

## Entries

### DD-017. The dashboards are vendored unchanged and built with dart-sass on Node 24

- **Status:** Proposed
- **Increment:** 0.6
- **Date:** 2026-10-17

**Decision.** `apps/aurelius-atlas-dashboard/dashboardv2` and `dashboardv3` are copies of the
`release-2.4.0` tag, byte for byte, with Atlas's `LICENSE` and `NOTICE`. Every change is a patch listed
in `PATCHES.md` and made in its own commit. The first patch replaces `node-sass` with `sass` (dart-sass)
in both `gruntfile.js` files and `package.json` files. Both dashboards are built with
`grunt build-minify`, as Atlas's Maven build does, in the hardened Node 24 image; only the built files
leave the build. The workspace's formatters, linters and hooks skip the vendored directories.

**Reason.** DD-001 asks for the dashboards unchanged; a vendored copy lets a reviewer prove that with a
diff against the tag. `node-sass` 9 is a native module with builds for Node 16 to 20 only, and Node 20
is past its end of life; dart-sass is pure JavaScript, the maintained Sass compiler, and `grunt-sass`
supports it. A trial build on Node 24 gave the same files as Atlas's toolchain on Node 20, with
identical JavaScript; only the two compiled stylesheets differ.

**Alternatives.** Build unchanged on Node 20: no patch, but an unsupported Node and a native compile in
every build. Download the tag at build time and apply patch files: a smaller repository, but the source
the build uses is not in review. Commit the built files: no legacy toolchain at all, but the shipped
files cannot be reviewed or rebuilt.

**Consequences.** The vendored `package-lock.json` files keep their 2020-era dependencies; they only run
inside the build container and are not part of the server image, so Dependabot does not watch them.
Moving to another Atlas release replaces both directories and re-applies `PATCHES.md`.
