# aurelius-atlas-ui

This library provides common UI components for Angular projects.

## API Documentation

This library is written in TypeScript, which is not covered by the generated API reference (mkdocstrings covers Python only here). Storybook, described below, is the component API reference; for the raw signatures, see the [source](<https://github.com/aureliusenterprise/aurelius-atlas/tree/main/libs/angular/aurelius-atlas-ui/src>).

## Installation

You can import `aurelius-atlas-ui` in your Angular project directly from the monorepo. It will be bundled with your application code and tree-shaken to include only the parts you use.

## Storybook

The `aurelius-atlas-ui` library includes a Storybook instance for interactive documentation and testing of the UI components. To run Storybook, execute the following command in the root of the monorepo:

```
nx run aurelius-atlas-ui:storybook
```

This will start the Storybook server and open the Storybook interface in your default web browser, where you can explore and interact with the UI components provided by the `aurelius-atlas-ui` library.
