import { ComponentFixture, TestBed } from "@angular/core/testing";
import { faTable } from "@fortawesome/free-solid-svg-icons";

import { TypeName } from "./type-name.component";

describe("TypeName", () => {
    let fixture: ComponentFixture<TypeName>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [TypeName],
        }).compileComponents();

        fixture = TestBed.createComponent(TypeName);
        fixture.detectChanges();
    });

    it("renders nothing without a name (UIC-17)", () => {
        expect(fixture.nativeElement.querySelector("span.icon-text")).toBeNull();
    });

    it("renders the icon, the name, and the title (UIC-17)", () => {
        fixture.componentRef.setInput("typeName", "m4i_dataset");
        fixture.componentRef.setInput("icon", faTable);
        fixture.componentRef.setInput("iconClass", "technical");
        fixture.detectChanges();

        const badge = fixture.nativeElement.querySelector("span.icon-text");
        expect(badge).toBeTruthy();
        expect(badge.getAttribute("title")).toBe("m4i_dataset");
        expect(badge.querySelector(".icon svg")).toBeTruthy();
        expect(badge.querySelector(".icon").classList.contains("technical")).toBe(true);
        expect(badge.textContent).toContain("m4i_dataset");
    });

    it("prefers the alias over the type name (UIC-17)", () => {
        fixture.componentRef.setInput("typeName", "m4i_dataset");
        fixture.componentRef.setInput("typeAlias", "Dataset");
        fixture.detectChanges();

        const badge = fixture.nativeElement.querySelector("span.icon-text");
        expect(badge.getAttribute("title")).toBe("Dataset");
        expect(badge.textContent).toBe("Dataset");
    });

    it("appends the base type when asked and an alias is set (UIC-17)", () => {
        fixture.componentRef.setInput("typeName", "m4i_dataset");
        fixture.componentRef.setInput("typeAlias", "Dataset");
        fixture.componentRef.setInput("showBaseTypeName", true);
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector("span.icon-text").textContent).toBe("Dataset\u00a0(m4i_dataset)");
    });

    it("omits the suffix without an alias, as the legacy guard did (UIC-17)", () => {
        fixture.componentRef.setInput("typeName", "m4i_dataset");
        fixture.componentRef.setInput("showBaseTypeName", true);
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector("span.icon-text").textContent).toBe("m4i_dataset");
    });

    it("hides the icon on request (UIC-17)", () => {
        fixture.componentRef.setInput("typeName", "m4i_dataset");
        fixture.componentRef.setInput("icon", faTable);
        fixture.componentRef.setInput("showIcon", false);
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector(".icon")).toBeNull();
    });

    it("hides the name on request (UIC-17)", () => {
        fixture.componentRef.setInput("typeName", "m4i_dataset");
        fixture.componentRef.setInput("showTypeName", false);
        fixture.detectChanges();

        expect(fixture.nativeElement.textContent.trim()).toBe("");
    });
});
