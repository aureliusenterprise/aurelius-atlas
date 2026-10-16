# aurelius-brand

This library provides the Aurelius brand styles and assets for use in Aurelius projects.

## Installation

You can include `aurelius-brand` styles in your project by adding them to your root `styles.scss` file:

```
@use "@aurelius/brand/src/main";
```

Then, you can include the `aurelius-brand` assets in your project by adding the following to your `angular.json`:

```
{
    "assets": [
        {
            "source": "libs/styles/aurelius-brand/assets",
            "target": "assets/aurelius-brand"
        }
    ]
}
```

Ensure the path points to the correct location of the `aurelius-brand` library.
