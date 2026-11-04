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

// The caller's fill (the editor's own sheet does the same, UIC-03: the
// colour comes from the Bulma danger ramp, no literal hex).
const fill = `
<style>
.aurelius-hold-story-button {
    overflow: hidden;
    position: relative;
}
.aurelius-hold-story-button::before {
    background-color: hsl(var(--bulma-danger-h), var(--bulma-danger-s), var(--bulma-danger-l));
    bottom: 0;
    content: "";
    left: 0;
    position: absolute;
    top: 0;
    transform: scaleX(var(--aurelius-hold-progress, 0));
    transform-origin: left center;
    width: 100%;
}
.aurelius-hold-story-button span {
    position: relative;
}
</style>
`;

const template = `${fill}
<button
    type="button"
    aurelius-atlas-ui-hold
    [holdFor]="holdFor"
    (held)="onHeld($event)"
    class="button is-small is-danger is-outlined aurelius-hold-story-button"
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
