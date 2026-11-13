/**
 * Per-instance id sequence shared by the components that mint element ids
 * (the pagination range line, the sortable table's select hint): two
 * instances on one page must not share an id, and the counter is
 * browser-tab-scoped like the ids it numbers.
 */
let instances = 0;

/**
 * Take the next instance number.
 * @returns a number unused by any earlier call in this tab
 */
export function nextInstanceId(): number {
    instances += 1;
    return instances;
}
