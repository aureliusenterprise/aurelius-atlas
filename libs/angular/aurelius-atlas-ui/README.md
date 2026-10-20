# aurelius-atlas-ui

Shared presentational Angular components for Aurelius frontends, styled with
Bulma design tokens from `@aurelius/atlas-brand`. Components are standalone and carry no
data-fetching logic — state and HTTP belong in the consuming app or in
`aurelius-atlas-data-access`.

Part of the template **spine**.

## Components

- `Accordion` — collapsible section with header slot
- `Card` — content card
- `DarkMode` + `DarkModeService` — theme toggle with persisted preference
- `Header` — application header bar
- `Hero` — page hero band with title, action slots, tab strip
- `Modal` — overlay dialog (plain content, or card anatomy with confirm/cancel)
- `Pagination` — page navigation
- `SearchField` — search box with submit and clear (Aurelius simple-search-input)
- `SortableTable` + `TableColumn`/`TableRow` — header-click sorting, paging,
  row selection; columns and rows declared as `ng-template` blocks

Every component ships a Storybook story (`.stories.ts`); the interactive ones
(`Accordion`, `Modal`, `SearchField`, `SortableTable`) also ship `play()`
interaction tests. Shared chrome strings ("Previous", "Toggle content", …) are
`i18n` units keyed by the legacy `components.*` dictionary paths; caller text
is passed as content nodes.

## Storybook

```bash
nx storybook aurelius-atlas-ui            # dev server on port 4400
nx build-storybook aurelius-atlas-ui      # static build
nx static-storybook aurelius-atlas-ui     # serve the static build on port 4500
nx test-storybook aurelius-atlas-ui       # interaction tests (Chromatic-ready)
```

## Usage

```ts
import { Card, Pagination } from "aurelius-atlas-ui";
```

Built with `ng-packagr-lite` (`nx build aurelius-atlas-ui` produces the distributable
package).
