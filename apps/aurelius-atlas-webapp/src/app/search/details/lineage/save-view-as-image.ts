import { Injectable, inject } from "@angular/core";
import html2canvas from "html2canvas";

import { APP_CONFIG } from "../../../tokens";
import { Session } from "../../../shell/session.service";
import type { Ar3View } from "./parse-ar3";
import { addTextMetadata, binaryStringToBytes, bytesToBinaryString } from "./png-metadata";

/**
 * The drawing surface the converter needs (LDG-30). Every browser API the
 * save flow touches sits behind this seam so the unit spec can stub the
 * canvas/URL layer — the serialize → draw → PNG path, the fallback, and the
 * download all run against a stub surface without a real canvas.
 */
export interface RasterSurface {
    /** Serialize a node to its XML text (the flow's `XMLSerializer`). */
    serialize(node: Node): string;
    /** A blob URL for the serialized svg. */
    createObjectUrl(blob: Blob): string;
    /** Release a URL handed out by {@link createObjectUrl}. */
    revokeObjectUrl(url: string): void;
    /** Load a URL into an image element. */
    loadImage(url: string): Promise<HTMLImageElement>;
    /** A `width` x `height` canvas element. */
    createCanvas(width: number, height: number): HTMLCanvasElement;
    /** Draw the loaded image onto the canvas at the origin. */
    drawImage(canvas: HTMLCanvasElement, image: HTMLImageElement): void;
    /** The canvas's PNG bytes as a binary string. */
    canvasToPng(canvas: HTMLCanvasElement): Promise<string>;
    /** Hand the bytes to the browser as a file download. */
    download(png: string, filename: string): void;
}

/** The surface's real implementation — every browser call of the save flow. */
const domSurface: RasterSurface = {
    serialize: (node) => new XMLSerializer().serializeToString(node),
    createObjectUrl: (blob) => URL.createObjectURL(blob),
    revokeObjectUrl: (url) => URL.revokeObjectURL(url),
    loadImage: (url) =>
        new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => resolve(img);
            // The legacy waited for `onload` only, so a load that failed
            // hung the save forever; here it rejects, which sends the flow
            // to the fallback exactly like a failed draw does.
            img.onerror = () => reject(new Error("the serialized svg did not load"));
            img.src = url;
        }),
    createCanvas: (width, height) => {
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        return canvas;
    },
    drawImage: (canvas, image) => {
        const ctx = canvas.getContext("2d");
        if (ctx === null) {
            throw new Error("the canvas has no 2d context");
        }
        ctx.drawImage(image, 0, 0);
    },
    canvasToPng: async (canvas) => {
        const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob((result) => resolve(result)));
        if (blob === null) {
            // A tainted canvas answers null (the legacy returned "" here and
            // skipped the save silently); throwing sends it to the fallback.
            throw new Error("the canvas could not be exported");
        }
        return bytesToBinaryString(new Uint8Array(await blob.arrayBuffer()));
    },
    download: (png, filename) => {
        // The download rides an anchor `download` (no `file-saver` — the
        // spec's deviation). The legacy's btoa/blob round trip carries the
        // same bytes, so the direct blob is equivalent.
        const blob = new Blob([binaryStringToBytes(png)], { type: "image/png" });
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = filename;
        anchor.click();
        URL.revokeObjectURL(url);
    },
};

/**
 * Save the drawn view as a PNG (LDG-30/LDG-31, DD-398): the legacy
 * `SaveViewAsImageService`, ported. The converter runs two paths over the
 * viewer's `<svg>` — serialize a dimension-fixed clone to a blob URL, load
 * it as an image, draw it onto a canvas, and read the canvas back; when that
 * fails (the `foreignObject` labels break the canvas export on some engines,
 * the legacy's comment) the container renders through html2canvas instead.
 * The bytes then gain one `tEXt` chunk per metadata field (LDG-31's writer)
 * and download as `${view name}.png`.
 *
 * The metadata reads this app's runtime values (DD-398): `Software` composes
 * from `/config.json` (`APP_CONFIG`, LDG-07's file) where the legacy baked
 * `git-version.json`, and `Author` is the signed-in user's email claim where
 * the legacy read its authentication store; `Source` is the constant the
 * legacy's lineage page always wrote — it had no repository project/branch.
 * Fields with no value ship no chunk (LDG-31's skip).
 *
 * The legacy reset the zoom around the save (LDG-29, held in its component);
 * DD-407 dropped that — the viewer converts the svg as it stands, so the
 * picture shows the reader's own pan/zoom. The one-conversion-at-a-time
 * subject of the legacy collapses to the viewer's save flag: the flow is a
 * single awaited call here.
 */
@Injectable({ providedIn: "root" })
export class SaveViewAsImage {
    private readonly session = inject(Session);
    private readonly config = inject(APP_CONFIG);

    /**
     * Convert the svg and download it under the view's name (the legacy's
     * `saveViewAsImage`).
     * @param svg the viewer's drawing element
     * @param width the container's measured width
     * @param height the container's measured height
     * @param view the view being drawn (its name and description are metadata)
     * @param surface the drawing seam (the real one unless a test stubs it)
     */
    async save(
        svg: SVGElement,
        width: number,
        height: number,
        view: Ar3View,
        surface: RasterSurface = domSurface,
    ): Promise<void> {
        const png = await this.convert(svg, width, height, surface);
        // LDG-31's field list, in the legacy's order. `Creation Time` is the
        // epoch-milliseconds value the legacy's lodash `now()` wrote.
        const metadata = {
            Title: view.name,
            Author: this.session.email(),
            Description: view.description,
            "Creation Time": String(Date.now()),
            Software: `Aurelius Atlas/${this.config.appName}/${this.config.appVersion}`,
            Source: "Generated model",
        };
        surface.download(addTextMetadata(png, metadata), `${view.name}.png`);
    }

    /** The legacy's `handleConvert`: the main path, the fallback on failure. */
    private async convert(svg: SVGElement, width: number, height: number, surface: RasterSurface): Promise<string> {
        try {
            return await this.drawSvgToCanvas(svg, width, height, surface);
        } catch {
            // Some engines cannot export an svg holding foreign objects
            // (the legacy's comment) — the slower path draws the container.
            return await this.drawHtmlToCanvas(svg, width, height, surface);
        }
    }

    /** The legacy's `drawSVG2Canvas`. */
    private async drawSvgToCanvas(
        svg: SVGElement,
        width: number,
        height: number,
        surface: RasterSurface,
    ): Promise<string> {
        // Firefox needs fixed dimensions on the svg before it draws to a
        // canvas (the legacy's rule, kept verbatim).
        const copy = svg.cloneNode(true) as SVGElement;
        copy.setAttribute("width", String(width));
        copy.setAttribute("height", String(height));

        const blob = new Blob([surface.serialize(copy)], { type: "image/svg+xml" });
        const url = surface.createObjectUrl(blob);
        const image = await surface.loadImage(url);
        surface.revokeObjectUrl(url);

        const canvas = surface.createCanvas(width, height);
        surface.drawImage(canvas, image);
        return surface.canvasToPng(canvas);
    }

    /** The legacy's `drawHTML2Canvas` — the fallback over the container. */
    private async drawHtmlToCanvas(
        svg: SVGElement,
        width: number,
        height: number,
        surface: RasterSurface,
    ): Promise<string> {
        const container = svg.parentElement;
        if (container === null) {
            throw new Error("the svg has no container to render");
        }
        const canvas = await html2canvas(container, {
            logging: false,
            width,
            height,
            scrollX: -window.scrollX,
            scrollY: -window.scrollY,
            // html2canvas renders its own clone of the document — the
            // legacy's fix-ups apply the fixed dimensions there.
            onclone: (clonedDocument: Document) => {
                const cloned = clonedDocument.getElementById("screenshot-container");
                if (cloned === null) {
                    return;
                }
                if (cloned.parentElement !== null) {
                    cloned.parentElement.style.display = "inline";
                }
                cloned.style.width = `${width}px`;
                cloned.style.height = `${height}px`;
            },
        });
        return surface.canvasToPng(canvas);
    }
}
