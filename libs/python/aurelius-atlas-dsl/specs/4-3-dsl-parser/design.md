# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-240. The DSL parser is generated from Atlas's own grammar

- **Status:** Proposed
- **Increment:** 4.3
- **Date:** 2026-10-30

**Decision.** `aurelius-atlas-dsl` keeps Atlas's `AtlasDSLLexer.g4` and `AtlasDSLParser.g4` unchanged in
`grammar/` and generates its lexer and parser from them with the ANTLR 4.13.2 tool (`npx nx generate-parser
aurelius-atlas-dsl`, Java needed only then). The generated modules are committed in
`aurelius_atlas_dsl/generated` and run on `antlr4-python3-runtime`, pinned to the tool's version. They are
left out of ruff, pyright, coverage, Sonar, the hooks, the traceability check and the increment's line budget:
nobody writes or reviews them.

**Reason.** The grammar is ambiguous and its lexer has quirks a client can see: the longest match decides
between a keyword and a name (`fromDate`, `db.name`, `a.b.c` as `a.b` and `.c`), a sign joins a number (`a -5`
is two sources), and ANTLR's adaptive prediction picks among the readings of `singleQrySrc`. Generating from
the same grammar reproduces all of it, and ANTLR's syntax error messages, which Atlas puts in
`INVALID_DSL_QUERY`. Every query of Atlas's DSL tests reads as Atlas reads it. A warm parse takes about 13 ms.

**Alternatives.** A hand-written recursive descent parser: no runtime dependency and faster, but every lexer
rule and every ambiguity resolution re-derived by hand, and ANTLR's error messages imitated. A parser library
such as Lark: a second grammar to keep equal to Atlas's. ANTLR 4.7, Atlas's own version: its Python runtime
dates from 2017 and is no longer maintained; 4.13 runs the same parsing algorithm.

**Consequences.** A grammar change is Atlas's grammar changed and the package regenerated, never the generated
code edited. The runtime is a pure-Python dependency without type information; `tree_builder` reads the
contexts through small typed helpers.

### DD-241. The parse tree is handed on as typed, immutable nodes

- **Status:** Proposed
- **Increment:** 4.3
- **Date:** 2026-10-30

**Decision.** `parse` returns a tree of frozen dataclasses (`dsl_tree`), not ANTLR's contexts: one node per
grammar rule that `DSLVisitor` reads, named after it, a choosing rule as the union of its alternatives. Every
node keeps its `getText()`, and an operator, sort order or literal the text it was written with besides its
kind.

**Reason.** `DSLVisitor` and `GremlinQueryComposer` work on rule texts (`getText()`) and on which alternative
matched; the nodes keep both, so 4.4 can port that logic, Atlas's quirks included (it upper-cases the
operator's spelling before looking it up). Typed nodes let pyright check 4.4's composer and keep the generated
code behind one module; equality makes trees easy to assert in tests.

**Alternatives.** Hand ANTLR's contexts to 4.4 as Java does: the closest port, but untyped, mutable and tied
to the generated code. An abstract tree that folds Atlas's rules into precedence (`and` before `or`): Atlas
joins conditions left to right, and the folding belongs to the composer that reproduces it.

**Consequences.** 4.4 composes Elasticsearch queries from `dsl_tree` alone. A grammar change touches
`dsl_tree` and `tree_builder` too.
