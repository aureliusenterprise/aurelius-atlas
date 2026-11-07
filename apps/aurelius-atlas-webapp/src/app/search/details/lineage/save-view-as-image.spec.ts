import { Injectable } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import { signal } from "@angular/core";
import { zoomIdentity, type ZoomTransform } from "d3-zoom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { APP_CONFIG } from "../../../tokens";
import { Session } from "../../../shell/session.service";
import type { Ar3View } from "./parse-ar3";
import { createChunk, joinChunk, splitChunk } from "./png-metadata";
import { saveAroundZoomReset, SaveViewAsImage, type RasterSurface } from "./save-view-as-image";

/**
 * The save flow over a stubbed drawing surface (LDG-30's named stubs): the
 * serialize→draw→PNG path, the fallback taken when the first path throws,
 * the `${view name}.png` name, the metadata the bytes carry (LDG-31), and
 * the zoom reset-and-restore order (LDG-29).
 */

/** html2canvas, stubbed — the fallback's render target. */
const html2canvasMock = vi.hoisted(() => vi.fn());
vi.mock("html2canvas", () => ({ default: html2canvasMock }));

/** A minimal well-formed PNG binary string (the bytes the stubs hand back). */
function minimalPng(): string {
    const ihdr = String.fromCharCode(...[0, 0, 0, 1, 0, 0, 0, 1, 8, 6, 0, 0, 0]);
    const idat = String.fromCharCode(0x78, 0x9c, 0x62, 0x00, 0x01, 0x00, 0x00, 0x05, 0x00, 0x01);
    return joinChunk([createChunk("IHDR", ihdr), createChunk("IDAT", idat), createChunk("IEND", "")]);
}

/** The drawing seam's stub: every call recorded, the PNG handed back. */
function stubSurface(overrides: Partial<RasterSurface> = {}) {
    const calls: string[] = [];
    const surface: RasterSurface = {
        serialize: (node) => {
            calls.push("serialize");
            expect(node.nodeName).toBe("svg");
            return "<svg/>";
        },
        createObjectUrl: (blob) => {
            calls.push("createObjectUrl");
            expect(blob.type).toBe("image/svg+xml");
            return "blob:stub";
        },
        revokeObjectUrl: () => void calls.push("revokeObjectUrl"),
        loadImage: () => {
            calls.push("loadImage");
            return Promise.resolve({} as HTMLImageElement);
        },
        createCanvas: (width, height) => {
            calls.push("createCanvas");
            return { width, height } as HTMLCanvasElement;
        },
        drawImage: () => void calls.push("drawImage"),
        canvasToPng: () => {
            calls.push("canvasToPng");
            return Promise.resolve(minimalPng());
        },
        download: () => void calls.push("download"),
        ...overrides,
    };
    return { surface, calls };
}

/** The surface stub plus a capture of the downloaded bytes. */
function captureSurface(overrides: Partial<RasterSurface> = {}) {
    let download: { png: string; filename: string } | null = null;
    const { surface, calls } = stubSurface({
        ...overrides,
        download: (png, filename) => {
            calls.push("download");
            download = { png, filename };
        },
    });
    return { surface, calls, downloaded: () => download as { png: string; filename: string } };
}

const view = { name: "Lineage", description: "The lineage view" } as Ar3View;

function setup(email = "ada@example.org") {
    @Injectable()
    class StubSession {
        readonly email = signal(email);
    }
    TestBed.configureTestingModule({
        providers: [
            SaveViewAsImage,
            { provide: Session, useClass: StubSession },
            {
                provide: APP_CONFIG,
                useValue: { appName: "Aurelius Atlas Data Governance", appVersion: "7.22.0#abc1234" },
            },
        ],
    });
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    const container = document.createElement("div");
    container.id = "screenshot-container";
    container.appendChild(svg);
    return { service: TestBed.inject(SaveViewAsImage), svg };
}

describe("save-view-as-image (LDG-29/30/31)", () => {
    beforeEach(() => {
        html2canvasMock.mockReset();
    });

    it("LDG-30: the main path serializes, draws, and reads the canvas back", async () => {
        const { service, svg } = setup();
        const { surface, calls } = captureSurface();

        await service.save(svg, 640, 480, view, surface);

        // The legacy's order, and never the fallback.
        expect(calls).toEqual([
            "serialize",
            "createObjectUrl",
            "loadImage",
            "revokeObjectUrl",
            "createCanvas",
            "drawImage",
            "canvasToPng",
            "download",
        ]);
        expect(html2canvasMock).not.toHaveBeenCalled();
    });

    it("LDG-30: the clone carries the measured dimensions (the Firefox rule)", async () => {
        const { service, svg } = setup();
        let serializedWidth = "";
        let serializedHeight = "";
        const { surface } = stubSurface({
            serialize: (node) => {
                serializedWidth = (node as SVGElement).getAttribute("width") ?? "";
                serializedHeight = (node as SVGElement).getAttribute("height") ?? "";
                return "<svg/>";
            },
        });

        await service.save(svg, 640, 480, view, surface);

        // The original keeps no dimensions — only the clone gains them.
        expect([serializedWidth, serializedHeight]).toEqual(["640", "480"]);
        expect(svg.getAttribute("width")).toBeNull();
    });

    it("LDG-30: the fallback renders the container when the draw fails", async () => {
        const { service, svg } = setup();
        html2canvasMock.mockResolvedValue({} as HTMLCanvasElement);
        const { surface, calls } = captureSurface({
            loadImage: () => Promise.reject(new Error("the serialized svg did not load")),
        });

        await service.save(svg, 640, 480, view, surface);

        expect(html2canvasMock).toHaveBeenCalledTimes(1);
        // The fallback's render target is the svg's container element.
        expect(html2canvasMock.mock.calls[0]?.[0]).toBe(svg.parentElement);
        expect(calls).toContain("download");
        expect(calls).not.toContain("createCanvas");
    });

    it("LDG-30: the download carries the file name `${view name}.png`", async () => {
        const { service, svg } = setup();
        const { surface, downloaded } = captureSurface();

        await service.save(svg, 640, 480, view, surface);

        expect(downloaded().filename).toBe("Lineage.png");
    });

    it("LDG-31: the saved bytes carry the metadata chunks", async () => {
        const { service, svg } = setup();
        const { surface, downloaded } = captureSurface();

        await service.save(svg, 640, 480, view, surface);

        const texts = splitChunk(downloaded().png)
            .filter((chunk) => chunk.type === "tEXt")
            .map((chunk) => chunk.data.split("\u0000"));
        const [keyword, value] = texts[3] ?? [];
        expect(keyword).toBe("Creation Time");
        expect(value).toMatch(/^\d{13}$/u); // epoch milliseconds (lodash now()'s shape)
        expect(texts).toEqual([
            ["Title", "Lineage"],
            ["Author", "ada@example.org"],
            ["Description", "The lineage view"],
            ["Creation Time", expect.any(String)],
            ["Software", "Aurelius Atlas/Aurelius Atlas Data Governance/7.22.0#abc1234"],
            ["Source", "Generated model"],
        ]);
    });

    it("LDG-31: an absent email claim ships no Author chunk (DD-398's skip)", async () => {
        const { service, svg } = setup("");
        const { surface, downloaded } = captureSurface();
        // A lineage view usually has no documentation (LDG-11's empty read).
        const bareView = { ...view, description: "" };

        await service.save(svg, 640, 480, bareView, surface);

        const keywords = splitChunk(downloaded().png)
            .filter((chunk) => chunk.type === "tEXt")
            .map((chunk) => chunk.data.split("\u0000")[0]);
        expect(keywords).not.toContain("Author");
        // The empty description skips too; Title, time, software, source stay.
        expect(keywords).not.toContain("Description");
        expect(keywords).toContain("Title");
    });

    it("LDG-29: the save runs at the identity transform and restores the old one", async () => {
        const order: string[] = [];
        const saved = zoomIdentity.translate(12, 20).scale(2);
        let inPlace: ZoomTransform = saved;
        await saveAroundZoomReset(
            () => {
                order.push("resetZoom");
                const previous = inPlace;
                inPlace = zoomIdentity;
                return previous;
            },
            (previous) => {
                order.push("setZoom");
                inPlace = previous;
            },
            async () => {
                order.push("save");
                // The conversion measures at identity (the legacy's rule).
                expect(inPlace).toBe(zoomIdentity);
            },
        );

        expect(order).toEqual(["resetZoom", "save", "setZoom"]);
        // The reader's view comes back exactly as left.
        expect(inPlace.toString()).toBe(saved.toString());
    });
});
