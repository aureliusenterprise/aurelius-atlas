import { ComponentFixture, TestBed } from "@angular/core/testing";

import { Markdown } from "./markdown.component";

describe("Markdown", () => {
    let fixture: ComponentFixture<Markdown>;

    const setMarkdown = (source: string) => {
        fixture.componentRef.setInput("markdown", source);
        fixture.detectChanges();
        return fixture.nativeElement.querySelector(".aurelius-markdown") as HTMLElement;
    };

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [Markdown],
        }).compileComponents();

        fixture = TestBed.createComponent(Markdown);
        // No detectChanges here: the markdown input is required and the
        // first render happens in setMarkdown, once a value exists.
    });

    it("renders plain markdown into the content block (DD-321)", () => {
        const content = setMarkdown("Hello **world**.");
        expect(content.classList.contains("content")).toBe(true);
        expect(content.querySelector("strong")!.textContent).toBe("world");
    });

    it("maps a heading onto the Bulma title ramp (DD-321)", () => {
        const content = setMarkdown("## Section");
        const heading = content.querySelector("h2")!;
        expect(heading.classList.contains("title")).toBe(true);
        expect(heading.classList.contains("is-2")).toBe(true);
        expect(heading.textContent).toBe("Section");
    });

    it("maps a blockquote onto the Bulma message (DD-321)", () => {
        const content = setMarkdown("> quoted");
        const message = content.querySelector("article.message")!;
        expect(message.querySelector(".message-body")!.textContent).toContain("quoted");
    });

    it("maps a table onto the striped Bulma table (DD-321)", () => {
        const content = setMarkdown("| a | b |\n| - | - |\n| 1 | 2 |");
        const container = content.querySelector("div.table-container")!;
        const table = container.querySelector("table.table")!;
        expect(table.classList.contains("is-striped")).toBe(true);
        expect(table.querySelectorAll("thead th")).toHaveLength(2);
        expect(table.querySelectorAll("tbody td")).toHaveLength(2);
    });

    it("maps an image onto the Bulma figure (DD-321)", () => {
        const content = setMarkdown("![alt text](https://example.test/pic.png)");
        const figure = content.querySelector("figure.image")!;
        const img = figure.querySelector("img")!;
        expect(img.getAttribute("alt")).toBe("alt text");
        expect(img.getAttribute("src")).toBe("https://example.test/pic.png");
    });

    it("drops a javascript: link through Angular sanitization (DET-10, DD-321)", () => {
        const content = setMarkdown("[click](javascript:alert(1))");
        const link = content.querySelector("a");
        // Angular's sanitizer neutralizes the dangerous scheme by prefixing
        // it with `unsafe:` (or dropping the href) — the browser then never
        // runs it. What must never survive is the bare scheme.
        expect(/^javascript:/i.test(link?.getAttribute("href") ?? "kept")).toBe(false);
    });

    it("strips raw script markup from markdown (DET-10, DD-321)", () => {
        const content = setMarkdown("<script>window.x=1</script>plain");
        expect(content.querySelector("script")).toBeNull();
        expect(content.textContent).toContain("plain");
    });
});
