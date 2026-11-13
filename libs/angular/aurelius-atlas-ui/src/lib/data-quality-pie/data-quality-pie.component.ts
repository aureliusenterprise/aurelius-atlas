import { ChangeDetectionStrategy, Component, HostBinding, input } from "@angular/core";

/**
 * The data-quality score circle (UIC-36, DD-447): the legacy
 * `models4insight-data-quality-pie`, rebuilt dumb — a green arc over a red
 * ring, sized in pixels, with the percent as the host's tooltip. It knows
 * nothing of `dqscore_*` documents: the caller turns its score into the
 * 0..100 number (the legacy multiplied the 0..1 raw by 100 at the call
 * site, and this keeps that contract on the input).
 *
 * The CSS is the legacy stylesheet (`data-quality-pie.component.scss`) as
 * a literal: the two stacked `.pie` layers are the ring and the arc, and
 * the `@property --p` registration is what lets the sweep animate. 7.25
 * wires the pies into the details pages' score boxes and the card badges
 * (UIC-39 projects this component); until then the stories are its screen
 * (DD-447 — dumb components ship with stories, not placeholder chrome).
 */
@Component({
    selector: "aurelius-atlas-ui-data-quality-pie",
    templateUrl: "./data-quality-pie.component.html",
    changeDetection: ChangeDetectionStrategy.OnPush,
    styles: `
        @property --p {
            syntax: "<number>";
            inherits: true;
            initial-value: 1;
        }

        :host {
            width: 100%;
            height: 100%;
        }

        .pie-container {
            --w: 100%;

            width: var(--w);
            height: var(--w);

            position: relative;
        }

        .pie {
            --p: 20;
            --c: black;

            width: var(--w);
            height: var(--w);

            aspect-ratio: 1;
            position: absolute;
        }

        .pie:before,
        .pie:after {
            content: "";
            position: absolute;
            border-radius: 50%;
        }

        .pie:before {
            inset: 0;
            background:
                radial-gradient(farthest-side, var(--c) 98%, #0000) top / var(--b) var(--b) no-repeat,
                conic-gradient(var(--c) calc(var(--p) * 1%), #0000 0);
            -webkit-mask: radial-gradient(farthest-side, #0000 calc(99% - var(--b)), #000 calc(100% - var(--b)));
            mask: radial-gradient(farthest-side, #0000 calc(99% - var(--b)), #000 calc(100% - var(--b)));
        }

        .pie:after {
            inset: calc(50% - var(--b) / 2);
            background: var(--c);
            transform: rotate(calc(var(--p) * 3.6deg)) translateY(calc(50% - var(--w) / 2));
        }

        .animate {
            animation: p 1s 0.5s both;
        }

        .no-round:before {
            background-size:
                0 0,
                auto;
        }

        .no-round:after {
            content: none;
        }

        @keyframes p {
            from {
                --p: 0;
            }
        }
    `,
})
export class DataQualityPie {
    /** The score, 0..100. The caller scales a 0..1 raw (the legacy's contract). */
    readonly value = input(0);

    /** The ring thickness in pixels (the legacy's `size`, default 4). */
    readonly size = input(4);

    /** The host tooltip: the percent, as the legacy `title` getter. */
    @HostBinding("title")
    protected get title(): string {
        return `${this.value()}%`;
    }

    /**
     * ALT-001 (WCAG 1.1.1): the ring is a graphic that carries the score,
     * so it is exposed as a named image — the tooltip alone never reaches
     * a screen reader.
     */
    @HostBinding("attr.role")
    protected readonly role = "img";

    /** ALT-001: the announced name, the percent in words. */
    @HostBinding("attr.aria-label")
    protected get ariaLabel(): string {
        return $localize`:@@components.dataQualityPie.label:Data quality score ${this.value()}:value:%`;
    }
}
