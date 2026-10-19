# API Reference

Generated API documentation for the Aurelius Atlas workspace, rendered from the docstrings in each
project by [mkdocstrings](https://mkdocstrings.github.io/). The prose for _what a project is_ lives in
its `README.md`; the wiring for _how it is built and run_ lives in its `AGENTS.md` (ADR 003). This
tree is the reference for _what it exposes_: classes, functions, signatures, and examples.

Each page doubles as that component's **design documentation**: the technology-specific detail of
how the component works — settings and knob names, storage layout, protocol mechanics, ports,
commands. The [architecture](../architecture/index.md) trees state the technology-neutral
properties the component must keep. A page's **Design** section carries this detail, with the ADR
that owns each rule linked.

- [Apps](apps/index.md) — the services: the Atlas server and the template examples
- [Libs](libs/index.md) — the Python, Angular, and style libraries the apps consume
