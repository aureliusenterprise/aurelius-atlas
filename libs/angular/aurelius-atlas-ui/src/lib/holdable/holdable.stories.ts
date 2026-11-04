import type { Meta, StoryObj } from "@storybook/angular";
import { expect, fireEvent, waitFor } from "storybook/test";

import { Holdable } from "./holdable.directive";

/**
 * The press-and-hold confirmation for a destructive control (the legacy
 * `models4insight-holdable`): the directive fires `held(true)` only when the
 * pointer stays down for `holdFor` seconds, and `held(false)` on an early
 * release. The caller paints the fill from the `--aurelius-hold-progress`
 * custom property the directive sweeps on the host (7.7c, EDT-19).
 */
const meta: Meta<Holdable> = {
    component: Holdable,
    title: "Holdable",
};
export default meta;

type Story = StoryObj<Holdable>;

/** The `held` emissions the play() tests collect. */
const emissions: boolean[] = [];

// The caller's ring (the editor's own sheet does the same, UIC-03: the
// colour comes from the Bulma danger ramp, no literal hex). The ring rides
// inside the solid button's edge and closes clockwise as the hold runs.
const fill = `
<style>
.aurelius-hold-story-button::before {
    background-image: conic-gradient(
        from 0deg,
        transparent calc(var(--aurelius-hold-progress, 0) * 360deg),
        var(--bulma-danger-invert) calc(var(--aurelius-hold-progress, 0) * 360deg)
    );
    border-radius: inherit;
    bottom: 3px;
    content: "";
    left: 3px;
    mask: linear-gradient(#000 0 0) exclude, linear-gradient(#000 0 0) center /
        calc(100% - 4px) calc(100% - 4px) no-repeat;
    pointer-events: none;
    position: absolute;
    right: 3px;
    top: 3px;
}
</style>
`;

const template = `${fill}
<button
    type="button"
    aurelius-atlas-ui-hold
    [holdFor]="holdFor"
    (held)="onHeld($event)"
    class="button is-small is-danger aurelius-hold-story-button"
><span>Hold to delete</span></button>
`;

const host = (args: Record<string, unknown>) => ({
    props: {
        ...args,
        onHeld: (confirmed: boolean) => emissions.push(confirmed),
    },
    template,
});

/**
 * A full hold confirms: the play() presses, watches the fill grow (the
 * custom property climbs past 0), and waits out the second, after which
 * `held` fires true once.
 */
export const CompletedHold: Story = {
    args: { holdFor: 1 },
    play: async ({ canvasElement }) => {
        emissions.length = 0;
        const button = canvasElement.querySelector<HTMLButtonElement>(".aurelius-hold-story-button");
        if (!button) throw new Error("the button is missing");

        fireEvent.pointerDown(button);
        await waitFor(() =>
            expect(Number(button.style.getPropertyValue("--aurelius-hold-progress"))).toBeGreaterThan(0),
        );
        await waitFor(() => expect(emissions).toEqual([true]), { timeout: 3000 });
        // The fill clears after the outcome and a longer hold does not re-fire.
        expect(button.style.getPropertyValue("--aurelius-hold-progress")).toBe("0");
        fireEvent.pointerUp(button);
        expect(emissions).toEqual([true]);
    },
    render: host,
};

/** A quick tap cancels: the release before the time ends fires `held(false)` and deletes nothing. */
export const EarlyRelease: Story = {
    args: { holdFor: 1 },
    play: async ({ canvasElement }) => {
        emissions.length = 0;
        const button = canvasElement.querySelector<HTMLButtonElement>(".aurelius-hold-story-button");
        if (!button) throw new Error("the button is missing");

        fireEvent.pointerDown(button);
        fireEvent.pointerUp(button);
        expect(emissions).toEqual([false]);
        // The fill clears on the cancelled hold.
        expect(button.style.getPropertyValue("--aurelius-hold-progress")).toBe("0");
    },
    render: host,
};
