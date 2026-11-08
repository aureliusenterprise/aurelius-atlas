import { ChangeDetectionStrategy, Component, input, output } from "@angular/core";

/**
 * A clickable colour square (UIC-32, DD-421): the legacy
 * `ColorSquareComponent` ported. The square shows the current colour and
 * opens the platform's colour picker on a click; picking emits the new
 * hex. The engine is a native `input[type=color]` styled flat — the
 * legacy's `ngx-color-picker` popover stays out (DD-421), the same zero-
 * dependency deviation DD-420 set for the legend.
 *
 * `editable=false` draws the bare square with no picker — the legacy's
 * `enableColorPicker` off-state, for a surface that shows a colour but
 * must not change one.
 */
@Component({
    selector: "aurelius-atlas-ui-color-square",
    imports: [],
    templateUrl: "./color-square.component.html",
    styleUrl: "./color-square.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ColorSquare {
    /** The current colour, as a hex the square paints and the input starts from. */
    readonly color = input("#000000");

    /** Whether a click opens the picker. Off draws a plain square (UIC-32). */
    readonly editable = input(true);

    /** Accessible name of the picker — the caller localises it (the badge's pattern). */
    readonly label = input("Color");

    /** A new colour was picked, as a hex. */
    readonly colorPicked = output<string>();

    /** The native input answered (it fires on every change of its picker). */
    protected onInput(event: Event): void {
        this.colorPicked.emit((event.target as HTMLInputElement).value);
    }
}
