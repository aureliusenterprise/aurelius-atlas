# Data Governance

Governance in the terms the business uses: people discover and understand data, know who is
accountable for it, see how it flows and how sensitive it is, and can prove all of it. Concretely,
that is how Aurelius Atlas describes, classifies, connects, and accounts for data — the catalogue's
own subject: the type system, lineage, glossary, classifications, and audit trail. The rules live in
the increment [semantics specs](../conversion/increments/index.md); these pages assemble them into the
governance view.

| Page                                                        | Scope                                                                                 | Written by                         |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------- | ---------------------------------- |
| [Roles & Responsibilities](roles-and-responsibilities.md)   | Who owns and who may act: authorizer roles, dataset ownership                         | 6.2 (ADR 042)                      |
| [Data Dictionary](data-dictionary.md)                       | The type system as the catalogue's dictionary: typedefs, built-in models, inheritance | 1.6 (material exists from 1.1–1.5) |
| [Data Quality](data-quality.md)                             | Glossary, terms, business metadata, labels as quality signals                         | 5.2, 5.3                           |
| [Data Lineage](data-lineage.md)                             | Processes, inputs/outputs, depth and direction, on-demand lineage                     | 5.1                                |
| [Compliance & Auditability](compliance-and-auditability.md) | Entity audit events, classifications with validity, audit REST                        | 3.5, 6.2                           |

??? QUESTION "Every page here is Planned — where do I read the rules?"

    In the increment specs, which are written with the code and are the authority
    ([semantics specs](../conversion/increments/index.md)); the dictionary's material, for
    example, exists from increments 1.1–1.5 even though its page lands with 1.6. A `Planned`
    marker names the increment whose spec to read instead.
