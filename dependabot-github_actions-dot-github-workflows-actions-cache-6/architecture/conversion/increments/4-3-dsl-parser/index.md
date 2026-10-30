# 4.3 DSL parser

- **Status:** in progress
- **Pull request:** [\#163](<https://github.com/aureliusenterprise/aurelius-atlas/pull/163>)
- **Records:** DD-240, DD-241, DV-88; relies on DD-002, DD-023

The Atlas DSL as Atlas reads it: `AtlasDSL.Parser` turns a query string into the parse tree of `AtlasDSLParser.g4`, and `AtlasDSL.QueryMetadata` reads its clauses and limits. Aurelius Atlas generates its lexer and parser from Atlas's own grammar (DD-240) and hands the tree on as a typed syntax tree (DD-241), which increment 4.4 composes into Elasticsearch queries.

## Scope

A new library, `aurelius-atlas-dsl` (DD-002):

| Module | Ports |
| --- | --- |
| `aurelius_atlas_dsl.generated` | `AtlasDSLLexer`, `AtlasDSLParser`, generated (DD-240) |
| `aurelius_atlas_dsl.atlas_dsl` | `AtlasDSL.Parser#parse`, `AtlasDSL.Validator`, `AtlasDSL.QueryMetadata` |
| `aurelius_atlas_dsl.dsl_tree` | the parse tree's contexts as typed nodes (DD-241) |
| `aurelius_atlas_dsl.tree_builder` | the contexts to those nodes |

`grammar/` holds `AtlasDSLLexer.g4` and `AtlasDSLParser.g4`, unchanged from Atlas, and the `generate-parser` target regenerates the package from them.

Not in this increment:

| What | Increment |
| --- | --- |
| `GET /api/atlas/v2/search/dsl`, `DSLVisitor`, `GremlinQueryComposer`, `IdentifierHelper` | 4.4 |
| `AtlasDSL.Translator` (the query from the tree and the type registry) | 4.4 |
| `AtlasDSL.Parser#isKeyword` (attribute names that are DSL keywords, 1.4 left them out) | not ported |

## Semantics

| Id | Rule |
| --- | --- |
| DSL-01 | A query is read into tokens by `AtlasDSLLexer.g4`, unchanged: keywords in any case, the longest match first and, of matches as long, the rule listed first; a quoted string (`"`, `'` or `` ` ``) and a name joined to keywords (`db.name`, `fromDate`) are each one identifier, and `a.b.c` is `a.b` and `.c`; spaces and comments are skipped |
| DSL-02 | A character no token begins with is dropped without an error, as Atlas leaves the lexer's errors to the console |
| DSL-03 | The tokens must form one `query` of `AtlasDSLParser.g4`, unchanged, up to the end of the input; where its rules allow more than one reading, the parser takes ANTLR's |
| DSL-04 | A query that does not parse fails with `INVALID_DSL_QUERY` (400, `ATLAS-400-00-059`), `Invalid DSL query: <query> \\| Reason: <message>. Please refer to Atlas DSL grammar for more information`, the message being ANTLR's for the last syntax error |
| DSL-05 | The tree keeps, of every rule, which alternative matched and its parts in order; and of every node its text as `getText()` gives it: its tokens' text joined without what was skipped. An operator, a sort order and a literal keep the text they were written with |
| DSL-06 | `QueryMetadata` tells whether the query has a `select`, a `groupby`, an `orderby` and a `limit`; the limit and offset are those of the `limit` and `offset` clauses, the offset 0 without its clause, both 0 without a `limit`; a transformation is needed with a `select` |
| DSL-07 | A limit or offset Java's `Integer.parseInt` cannot read (`limit 1e3`, `limit 3000000000`) fails with `INVALID_DSL_QUERY`, its reason naming the number (DV-88) |

## Java origin

Apache Atlas `release-2.4.0`:

- `repository/.../query/antlr4/AtlasDSLLexer.g4`, `AtlasDSLParser.g4`, and the classes ANTLR 4.7 generates from them
- `repository/.../query/AtlasDSL.java`: `Parser#parse`, `Validator`, `QueryMetadata`
- `repository/.../query/DSLVisitor.java`: which parts of the tree, and which of their texts, the composer reads (DSL-05 keeps all of them for 4.4)
- `intg/.../AtlasErrorCode.java`: `INVALID_DSL_QUERY`

## Deviations

DV-88: Atlas reads the limit and offset with `Integer.parseInt` and lets its `NumberFormatException` escape as an internal error; Aurelius Atlas answers `INVALID_DSL_QUERY`. ANTLR 4.13 generates the parser where Atlas used 4.7; the grammar and its reading are the same (DD-240), and no parity scenario shows a difference.

## Acceptance

- `libs/python/aurelius-atlas-dsl/tests/` — DSL-01 to DSL-07; `tests/fixtures/atlas_queries.json` holds every query of Atlas's `DSLQueriesTest`, `GremlinQueryComposerTest` and `DSLParsingTest`, each with its source line: those Atlas parses parse here, the eight of `DSLParsingTest` fail with ANTLR's message.
- `uv run pytest libs/python/aurelius-atlas-dsl/tests`, `npx nx test aurelius-atlas-dsl -c ci`.
- `uv run aurelius-atlas-trace check`.
