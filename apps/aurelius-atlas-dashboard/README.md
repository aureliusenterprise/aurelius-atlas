# aurelius-atlas-dashboard

The two user interfaces of Apache Atlas 2.4.0, `dashboardv2` and `dashboardv3`, vendored from the
`release-2.4.0` tag and changed only by the patches in [`PATCHES.md`](PATCHES.md)
([DD-017](../../docs/architecture/conversion/design-log.md#dd-017-the-dashboards-are-vendored-unchanged-and-built-with-dart-sass-on-node-24)).

Introduced by increment [0.6](../../docs/architecture/conversion/increments/0-6-dashboards.md). The
`aurelius-atlas-server` serves them where Atlas does: `dashboardv2` at `/` and `dashboardv3` at `/n/`
([DD-018](../../docs/architecture/conversion/design-log.md#dd-018-the-server-serves-the-dashboards-from-the-apis-origin)).
Until the later increments port the endpoints they call, the dashboards load and report errors for
those calls.

## Building

```bash
npx nx build aurelius-atlas-dashboard
```

The build runs `grunt build-minify` for both dashboards inside the hardened Node 24 image, as Atlas's
Maven build does, and writes only the static files to `dist/`. It needs Docker with `buildx`.

## License

The vendored source is Apache Atlas's, under the Apache License 2.0; see [`LICENSE`](LICENSE) and
[`NOTICE`](NOTICE).
