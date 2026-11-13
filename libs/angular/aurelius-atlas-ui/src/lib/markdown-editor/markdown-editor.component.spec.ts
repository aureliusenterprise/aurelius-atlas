import { Component, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { disabled, FieldTree, FormField, form, required } from "@angular/forms/signals";

import { MarkdownEditor } from "./markdown-editor.component";

/** The caller's form around the field — the directive binds through `[formField]` (DD-354). */
@Component({
    imports: [MarkdownEditor, FormField],
    template: `
        <form>
            <label for="field-id">Description</label>
            <aurelius-atlas-ui-markdown-editor
                [formField]="state().description"
                textareaId="field-id"
                writeLabel="Write"
                previewLabel="Preview"
                placeholder="Type markdown"
            />
        </form>
    `,
})
class HostComponent {
    private readonly model = signal({ description: "" });

    /** The flipped side of the schema's `disabled` rule (the disable test). */
    readonly off = signal(false);

    readonly state = signal<FieldTree<{ description: string }>>(
        form(this.model, (path) => {
            required(path.description);
            disabled(path.description, { when: () => this.off() });
        }),
    );
}

describe("MarkdownEditor (UIC-26)", () => {
    let fixture: ComponentFixture<HostComponent>;
    let host: HostComponent;

    const textarea = () => fixture.nativeElement.querySelector("textarea") as HTMLTextAreaElement;
    const tabs = () => [...fixture.nativeElement.querySelectorAll('[role="tab"]')] as HTMLElement[];
    const writePane = () => fixture.nativeElement.querySelector('[role="tabpanel"]:not([hidden])') as HTMLElement;

    const typeInto = (value: string) => {
        const area = textarea();
        area.value = value;
        area.dispatchEvent(new Event("input"));
        fixture.detectChanges();
    };

    beforeEach(async () => {
        await TestBed.configureTestingModule({ imports: [HostComponent] }).compileComponents();
        fixture = TestBed.createComponent(HostComponent);
        host = fixture.componentInstance;
        fixture.detectChanges();
    });

    it("starts on the Write tab with the tab pair wired (UIC-26)", () => {
        const [write, preview] = tabs();
        expect(fixture.nativeElement.querySelector('[role="tablist"]')).toBeTruthy();
        expect(write.getAttribute("aria-selected")).toBe("true");
        expect(preview.getAttribute("aria-selected")).toBe("false");
        expect(write.textContent?.trim()).toBe("Write");
        expect(preview.textContent?.trim()).toBe("Preview");
        // The active tab names its pane; the pane names its tab back.
        expect(write.getAttribute("aria-controls")).toBe(writePane().id);
        expect(writePane().getAttribute("aria-labelledby")).toBe(write.id);
    });

    it("switches panes on the tab, moving aria-selected and hiding the inactive pane (UIC-26)", () => {
        const [write, preview] = tabs();
        preview.click();
        fixture.detectChanges();

        expect(write.getAttribute("aria-selected")).toBe("false");
        expect(preview.getAttribute("aria-selected")).toBe("true");
        const writeArea = fixture.nativeElement.querySelector(".aurelius-markdown-editor-write") as HTMLElement;
        const previewArea = fixture.nativeElement.querySelector(".aurelius-markdown-editor-preview") as HTMLElement;
        // Both panes stay mounted (DD-352): the inactive one only hides.
        expect(writeArea.isConnected).toBe(true);
        expect(writeArea.hidden).toBe(true);
        expect(previewArea.hidden).toBe(false);
    });

    /** The description field's state — a tree node is a signal of its state. */
    const description = () => host.state().description();

    it("writes the bound field's value into the textarea (UIC-26)", () => {
        description().value.set("# Seeded heading");
        fixture.detectChanges();

        expect(textarea().value).toBe("# Seeded heading");
    });

    it("sends the typed source back to the bound model (UIC-26)", () => {
        typeInto("## Edited");

        expect(description().value()).toBe("## Edited");
    });

    it("marks the field touched on blur, through the contract's touch output (UIC-26)", () => {
        const area = textarea();
        area.dispatchEvent(new Event("blur"));
        fixture.detectChanges();

        expect(description().touched()).toBe(true);
    });

    it("renders the typed markdown live in the preview pane (UIC-26, DD-321)", () => {
        typeInto("# Live heading");
        tabs()[1].click();
        fixture.detectChanges();

        const previewArea = fixture.nativeElement.querySelector(".aurelius-markdown-editor-preview");
        const heading = previewArea.querySelector("h1") as HTMLElement;
        // The shared block's own rendering: the Bulma title ramp proves the
        // one renderer, not a second marked call.
        expect(heading.classList.contains("title")).toBe(true);
        expect(heading.textContent).toBe("Live heading");
    });

    it("keeps the textarea's value across a tab switch (UIC-26, DD-352)", () => {
        typeInto("Kept while hidden");
        const before = textarea().value;
        tabs()[1].click();
        fixture.detectChanges();
        tabs()[0].click();
        fixture.detectChanges();

        expect(textarea().value).toBe(before);
    });

    it("seats the caller's textareaId on the textarea and pairs the label (UIC-26)", () => {
        expect(textarea().id).toBe("field-id");
        const label = fixture.nativeElement.querySelector("label") as HTMLLabelElement;
        expect(label.htmlFor).toBe("field-id");
    });

    it("paints is-danger only while the field is invalid and marked (UIC-26)", () => {
        expect(textarea().classList.contains("is-danger")).toBe(false);

        description().markAsTouched();
        fixture.detectChanges();
        expect(textarea().classList.contains("is-danger")).toBe(true);

        // Reset clears touched/dirty and carries a valid value (required).
        description().reset("valid again");
        fixture.detectChanges();
        expect(textarea().classList.contains("is-danger")).toBe(false);
    });

    it("follows a caller's markAsTouched on the root (the refused-Save state, UIC-26)", () => {
        host.state()().markAsTouched();
        fixture.detectChanges();

        expect(textarea().classList.contains("is-danger")).toBe(true);
    });

    it("disables the textarea while the field is disabled (UIC-26)", () => {
        host.off.set(true);
        fixture.detectChanges();

        expect(textarea().disabled).toBe(true);

        host.off.set(false);
        fixture.detectChanges();
        expect(textarea().disabled).toBe(false);
    });

    it("carries the caller's placeholder without a string of its own (UIC-04, DD-136)", () => {
        expect(textarea().getAttribute("placeholder")).toBe("Type markdown");
    });

    it("pairs the panes without a caller id, on the counter fallback (UIC-26)", () => {
        const bare = TestBed.createComponent(MarkdownEditor);
        bare.detectChanges();
        const area = bare.nativeElement.querySelector('[role="tabpanel"]') as HTMLElement;
        const tab = bare.nativeElement.querySelector('[role="tab"]') as HTMLElement;

        expect(tab.getAttribute("aria-controls")).toBe(area.id);
        expect(area.id).toMatch(/^aurelius-markdown-editor-\d+-write$/);
    });

    it("runs the tab pair as native buttons with a roving tabindex (FORM-CUSTOM-002)", () => {
        const [write, preview] = tabs();

        // A real button needs no key handlers of its own — activation is the
        // element's; the inactive tab sits out of the tab order.
        expect(write.tagName).toBe("BUTTON");
        expect(write.getAttribute("type")).toBe("button");
        expect(preview.tagName).toBe("BUTTON");
        expect(write.getAttribute("tabindex")).toBe("0");
        expect(preview.getAttribute("tabindex")).toBe("-1");

        preview.click();
        fixture.detectChanges();

        expect(write.getAttribute("tabindex")).toBe("-1");
        expect(tabs()[1].getAttribute("tabindex")).toBe("0");
    });

    it("walks the tab pair with the arrow keys, carrying focus (FORM-CUSTOM-002)", () => {
        const press = (key: string) => {
            tabs()
                .find((tab) => tab.getAttribute("aria-selected") === "true")!
                .dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true }));
            fixture.detectChanges();
        };

        press("ArrowRight");
        expect(tabs()[1].getAttribute("aria-selected")).toBe("true");
        expect(document.activeElement).toBe(tabs()[1]);

        // Right wraps to the first tab; Left wraps back to the last.
        press("ArrowRight");
        expect(tabs()[0].getAttribute("aria-selected")).toBe("true");
        expect(document.activeElement).toBe(tabs()[0]);
        press("ArrowLeft");
        expect(tabs()[1].getAttribute("aria-selected")).toBe("true");

        // Home/End jump the ends.
        press("Home");
        expect(tabs()[0].getAttribute("aria-selected")).toBe("true");
        press("End");
        expect(tabs()[1].getAttribute("aria-selected")).toBe("true");
        expect(document.activeElement).toBe(tabs()[1]);
    });

    it("carries the caller's required and error-line ids onto the textarea (FORM-REQ-001, FORM-ERR-002)", () => {
        const bare = TestBed.createComponent(MarkdownEditor);
        bare.detectChanges();
        const area = () => bare.nativeElement.querySelector("textarea") as HTMLTextAreaElement;

        expect(area().required).toBe(false);
        expect(area().hasAttribute("aria-describedby")).toBe(false);
        expect(area().getAttribute("aria-invalid")).toBeNull();

        bare.componentRef.setInput("required", true);
        bare.componentRef.setInput("describedBy", "editor-description-error");
        bare.componentRef.setInput("invalid", true);
        bare.detectChanges();

        expect(area().required).toBe(true);
        expect(area().getAttribute("aria-describedby")).toBe("editor-description-error");
        expect(area().getAttribute("aria-invalid")).toBe("true");
    });
});
