# Design decisions

A cross-cutting build decision, not a roadmap increment: it delivers no rule and
no spec of its own (the DD-247 shape — a fix found by CI, no roadmap row). It
touches only `apps/aurelius-atlas-webapp/Dockerfile`. The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply.

## DD-876. The OTel builder calls auto/configure, not the top-level ./configure

- **Status:** Proposed
- **Increment:** cross-cutting (webapp image build; no roadmap row — found by e2e on 2026-11-25)
- **Date:** 2026-11-25
- **Supersedes:** –

**Decision.** The OTel-module build stage of the webapp image runs the source
tree's real entrypoint, `auto/configure`, instead of the top-level `./configure`
wrapper, when configuring nginx before the module build (the step that reads the
running binary's own configure arguments and adds `--with-compat`). Everything
else in the stage — the `nginx-stable-mod-dev~$NGINX_VER` pin, the versioned-dir
symlink, the patch-level check — stays.

**Reason.** Docker Hardened Images re-pushed the `dhi.io/nginx:1.30-alpine3.24-dev`
base under the same `1.30` tag: its `nginx-stable-mod-dev` source kit is now
1.30.8-r0, which ships the whole tree (`auto/`, `src/`, …) **without** the
top-level one-line `configure` wrapper. The build then failed at
`eval sh ./configure …` with `can't open './configure'`, which turned **every**
webapp `docker build` red — and so the `e2e` job of every open pull request,
whatever it changed — because each one builds this image. This is the exact
"apk's newest kit can run ahead of the image" case the Dockerfile's own comment
warns about; it reached the base image before any recipe change did.

**Considered and rejected.** _Pin the `-dev` base by digest to the last good
build_ — it unblocks today but hardcodes the 1.30.6 tree the recipe was written
against, so the next patch bump reproduces the break and re-pinning becomes
routine maintenance. _Pin `nginx-stable-mod-dev` to the exact version that
carries the wrapper_ — the wrapper is not a feature of a version, it is present
or absent depending on how dhi built and pushed that tag; pinning to it bets the
build on a packaging accident staying put. _Re-create the wrapper (`sh -c 'echo
sh auto/configure "\$@"' > configure`)_ — more moving parts for no gain, since
`auto/configure` already runs.

**Consequences.** The recipe now calls the entrypoint that is always present in
the tree, so it builds against either kit layout (with or without the wrapper)
and no patch bump re-breaks it. `auto/configure` reads its tree by relative path
(`. auto/options`) and must run from the source root — which the existing
`WORKDIR /usr/src/nginx-src` already sets — and it generates the same `objs/`
(`ngx_modules.c`, `ngx_auto_config.h`) the module's cmake step consumes; verified
end-to-end locally (`--target otel-verified` builds and prints "nginx 1.30.8 in
both stages"). The version comment in the Dockerfile moves to the kit's current
patch level as an example only — the recipe still reads it from the running
binary, so the number is illustrative and a future bump needs no edit. No
behaviour, rule, or string change; nothing in `java-map.md` or `deviations.md`.
