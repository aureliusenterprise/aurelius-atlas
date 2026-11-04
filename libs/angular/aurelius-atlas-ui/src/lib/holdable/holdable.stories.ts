import type { Meta, StoryObj } from "@storybook/angular";
import { expect, fireEvent, waitFor } from "storybook/test";

import { Holdable } from "./holdable.directive";

/**
 * The press-and-hold confirmation for a destructive control (the legacy
 * `models4insight-holdable`): the directive fires `held(true)` only when the
 * pointer stays down for `holdFor` seconds, and `held(false)` on an early
 * release. The caller grows a round donut arc clockwise with a plain CSS
 * animation that runs for the hold's own duration (7.7c, EDT-19). The base
 * is a plain Bulma button, and while held the button behaves like
 * `is-loading`: the label clears and the donut appears in its place.
 */
const meta: Meta<Holdable> = {
    component: Holdable,
    title: "Holdable",
};
export default meta;

type Story = StoryObj<Holdable>;

/** The `held` emissions the play() tests collect. */
const emissions: boolean[] = [];

// The base is a plain Bulma button that behaves like `is-loading` while the
// hold runs: the directive marks the host `data-aurelius-hold="holding"`, the
// label clears (Bulma's own `color: transparent !important`), and a donut in
// the spinner's place takes over — a 1em circle stroked 2px (the spinner's
// own weights) in `--bulma-loading-color`. The ring is an SVG circle stroke,
// so its edges are anti-aliased — a CSS `mask` over a border circle re-clips
// with hard, jagged edges. The circle's `pathLength` is 1, which lets
// `stroke-dasharray: 1` and one CSS animation of `stroke-dashoffset` draw the
// ring clockwise from the top (the SVG is rotated a quarter turn) with no
// per-frame JavaScript. The animation's duration is the hold itself: the
// button passes `holdFor` as `--aurelius-hold-duration`, so the ring is drawn
// whole exactly when the press has lasted long enough. An early release drops
// the `holding` state, which removes the animation, so the next press starts
// a fresh one from the top.
const donut = `<svg class="aurelius-hold-donut" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.5" [attr.pathLength]="1"></circle></svg>`;

const fill = `
<style>
@keyframes aurelius-hold-draw {
    from {
        stroke-dashoffset: 1;
    }
    to {
        stroke-dashoffset: 0;
    }
}
.aurelius-hold-donut {
    display: none;
    height: 1em;
    left: calc(50% - 0.5em);
    overflow: visible;
    position: absolute;
    top: calc(50% - 0.5em);
    transform: rotate(-90deg);
    width: 1em;
}
.aurelius-hold-donut > circle {
    fill: none;
    stroke: var(--bulma-loading-color);
    stroke-dasharray: 1;
    stroke-width: 2;
    vector-effect: non-scaling-stroke;
}
.aurelius-hold-button[data-aurelius-hold="holding"] {
    color: transparent !important;
}
.aurelius-hold-button[data-aurelius-hold="holding"] > .aurelius-hold-donut {
    display: block;
}
.aurelius-hold-button[data-aurelius-hold="holding"] > .aurelius-hold-donut > circle {
    animation: aurelius-hold-draw var(--aurelius-hold-duration, 3s) linear forwards;
}
</style>
`;

const template = `${fill}
<button
    type="button"
    aurelius-atlas-ui-hold
    [holdFor]="holdFor"
    [style.--aurelius-hold-duration]="holdFor + 's'"
    (held)="onHeld($event)"
    class="button is-danger aurelius-hold-button aurelius-hold-story-button"
><span>Hold to delete</span>${donut}</button>
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
        // The donut resets on the cancelled hold.
        expect(button.style.getPropertyValue("--aurelius-hold-progress")).toBe("0");
    },
    render: host,
};

/**
 * The animation itself, as shipped: the button is pinned to the holding state
 * and the real animation plays exactly once over the 3-second hold and stays
 * put — the label clears, the round donut grows clockwise from the top, and
 * when the time is up the ring is fully closed and holds there (the CSS
 * `forwards` fill). The play() asserts that one play and the closed end. The
 * editor's Delete rides this same look; this is the mock under review.
 */
export const ClosingOnce: Story = {
    play: async ({ canvasElement }) => {
        const circle = canvasElement.querySelector("circle");
        if (!circle) throw new Error("the donut is missing");
        // One play over the hold, then it holds closed (no loop).
        expect(getComputedStyle(circle).animationIterationCount).toBe("1");
        expect(getComputedStyle(circle).animationFillMode).toBe("forwards");
        // Once the time is up, the ring is fully closed and stays so.
        await waitFor(() => expect(getComputedStyle(circle).strokeDashoffset).toBe("0px"), {
            timeout: 5000,
        });
        await waitFor(() => expect(getComputedStyle(circle).strokeDashoffset).toBe("0px"), {
            timeout: 500,
        });
    },
    render: () => ({
        template: `${fill}
<button type="button" class="button is-danger aurelius-hold-button aurelius-hold-mock" data-aurelius-hold="holding" style="--aurelius-hold-duration: 3s; font-size: 22px; padding: 16px 28px;"><span>Hold to delete</span>${donut}</button>
<p class="is-size-7">The real animation, played once: the label clears and the round donut grows clockwise from the top for 3 seconds, then the ring is fully closed and holds. Press and hold the <em>Hold to delete</em> button in <strong>Completed Hold</strong> for the interactive one.</p>`,
    }),
};
