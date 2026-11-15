import { typeIcon } from "../meta/type-icons";
import { trailOf } from "./trail";

/**
 * The shared trail rule (VDR-06, DD-606, DD-616, VDR-11, DD-630): both
 * screens build their trail here, so the rule is pinned here too.
 */
describe("trailOf (VDR-06, VDR-11, DD-606/DD-630)", () => {
    const icon = (typeName: string) => typeIcon(typeName);
    const card = {
        guid: "e1",
        name: "cost_centre_code",
        typeName: "m4i_data_attribute",
        breadcrumb: [{ guid: "d1", name: "Finance", typeName: "m4i_data_domain" }],
    };

    it("answers the stored crumbs top down plus the entity's own crumb last (VDR-06)", () => {
        const trail = trailOf(card, icon);
        expect(trail.map((crumb) => crumb.guid)).toEqual(["d1", "e1"]);
        // The mapped type rides the app's icon (DET-26's resolver).
        expect(trail[0].icon).toBeTruthy();
    });

    it("answers nothing when the entity has no stored parent (VDR-11, DD-630)", () => {
        // The legacy guard wrapped the whole trail, own crumb included: a
        // parentless entity drew no trail, and its title already names it.
        expect(trailOf({ ...card, breadcrumb: [] }, icon)).toEqual([]);
        expect(trailOf({ ...card, breadcrumb: undefined }, icon)).toEqual([]);
        expect(trailOf({ guid: "e1", name: "solo", typeName: "DataSet" }, icon)).toEqual([]);
    });

    it("keeps the name, type, guid fallbacks on a filled trail (VDR-06, ASU-02)", () => {
        const trail = trailOf(
            {
                ...card,
                breadcrumb: [
                    { guid: "x1", name: null, typeName: "m4i_data_domain" },
                    { guid: "x2", name: "", typeName: null },
                ],
            },
            icon,
        );
        expect(trail.map((crumb) => crumb.name)).toEqual(["m4i_data_domain", "x2", "cost_centre_code"]);
    });
});
