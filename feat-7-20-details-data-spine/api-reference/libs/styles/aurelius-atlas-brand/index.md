# aurelius-atlas-brand

This library provides the Aurelius brand styles and assets for use in Aurelius projects.

## Installation

You can include `aurelius-atlas-brand` styles in your project by adding them to your root `styles.scss` file:

```
@use "@aurelius/atlas-brand/src/main";
```

Then, you can include the `aurelius-atlas-brand` assets in your project by adding the following to your `angular.json`:

```
{
    "assets": [
        {
            "source": "libs/styles/aurelius-atlas-brand/assets",
            "target": "assets/aurelius-atlas-brand"
        }
    ]
}
```

Ensure the path points to the correct location of the `aurelius-atlas-brand` library.
