# Specs

One directory per increment that touches `libs/python/aurelius-atlas-auth`: `N-M-slug/spec.md` (the
semantics, written before the code) with `design.md` (its `DD-NNN` entries) beside it.
New increments start from the [template](../../../../docs/architecture/conversion/increments/template.md)
([ADR 051][adr051]) and join the `specs` roots in the root `pyproject.toml`, so the
trace check reads them. They are not pages of the docs site; the roadmap of what
lands when is the [conversion index](../../../../docs/architecture/conversion/index.md#roadmap).

[adr051]: ../../../../docs/architecture/adr/051-the-conversion-proceeds-in-specified-increments.md
