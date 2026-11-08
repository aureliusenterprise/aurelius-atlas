/**
 * The connection path maths (LDG-14): the legacy
 * `libs/modelview2/src/lib/shapes/connection/modelview-connection.service.ts`
 * ported — `getShortestLineEndpoints` verbatim and the bendpoint walk
 * (`buildPath`/`buildPathFromSteps`/`pointToPoint`). A connection runs from
 * the source rectangle to the target's through the server's bendpoints: every
 * waypoint pair yields the straightest entry/exit points on the two surfaces
 * (a node contributes its rectangle, a bendpoint its point with zero extent),
 * and the polyline through those points is the drawn path.
 *
 * Two legacy branches stay with the explorer (DD-388/DD-389): connections
 * that end on another connection (`isConnection`, the explorer's nested
 * diagrams) and connections between nested rectangles (`areNested`, hidden in
 * the legacy); the shipped lineage layout emits neither — its nodes never
 * overlap and its connections only join nodes.
 *
 * The legacy emitted the path relative (`m0,0` + `l` deltas from the first
 * endpoint) with the group translated to it; this port emits the same
 * polyline as absolute coordinates in the model's own space, which the
 * viewer's bounds group shifts to the origin (LDG-15). Consecutive legs
 * join at the waypoint's two endpoint points; identical neighbours collapse
 * so a straight two-node line stays `M x1,y1 L x2,y2`.
 */

/** A drawn surface: a node rectangle or a bendpoint point (zero extent). */
export interface PathSurface {
    readonly x: number;
    readonly y: number;
    readonly width?: number;
    readonly height?: number;
}

/** One leg of a connection: from (x1,y1) on one surface to (x2,y2) on the next. */
interface Leg {
    readonly x1: number;
    readonly y1: number;
    readonly x2: number;
    readonly y2: number;
}

/**
 * The straightest connection between two parallel surfaces, one axis at a
 * time (the legacy's `getShortestLineEndpoints`, kept branch for branch):
 * surfaces apart get their facing edges; surfaces overlapping get the
 * overlap's centre on both.
 * @param sourcePos the source's near coordinate on the axis
 * @param sourceLength the source's extent on the axis
 * @param targetPos the target's near coordinate on the axis
 * @param targetLength the target's extent on the axis
 * @returns the source and target coordinates on the axis
 */
function shortestEndpoints(
    sourcePos: number,
    sourceLength: number,
    targetPos: number,
    targetLength: number,
): [number, number] {
    // Target is completely left of source. Draw connection to the edges.
    if (sourcePos > targetPos + targetLength) {
        return [sourcePos, targetPos + targetLength];
    }
    // Target is somewhat left of source. Center on the overlap.
    else if (sourcePos >= targetPos && sourcePos + sourceLength >= targetPos + targetLength) {
        const centre = sourcePos + (targetPos + targetLength - sourcePos) / 2;
        return [centre, centre];
    }
    // Target is completely right of source. Draw connection to the edges.
    else if (sourcePos + sourceLength < targetPos) {
        return [sourcePos + sourceLength, targetPos];
    }
    // Target is somewhat right of source. Center on the overlap.
    else if (sourcePos <= targetPos && sourcePos + sourceLength <= targetPos + targetLength) {
        const centre = targetPos + (sourcePos + sourceLength - targetPos) / 2;
        return [centre, centre];
    }
    // Target is both left and right of source. Center on source.
    else if (sourcePos > targetPos && sourcePos + sourceLength < targetPos + targetLength) {
        const centre = sourcePos + sourceLength / 2;
        return [centre, centre];
    }
    // Target is neither left nor right of source. Center on target.
    else {
        const centre = targetPos + targetLength / 2;
        return [centre, centre];
    }
}

/** The two-surface leg pair, both axes (the legacy's `pointToPoint`). */
function legBetween(source: PathSurface, target: PathSurface): Leg {
    const [x1, x2] = shortestEndpoints(source.x, source.width ?? 0, target.x, target.width ?? 0);
    const [y1, y2] = shortestEndpoints(source.y, source.height ?? 0, target.y, target.height ?? 0);
    return { x1, y1, x2, y2 };
}

/**
 * The drawn path of a connection (LDG-14): the source rectangle to the
 * target through the bendpoints.
 * @param source the source node's rectangle
 * @param target the target node's rectangle
 * @param bendpoints the connection's waypoints, in order
 * @returns the absolute SVG path, or empty when there is no leg to draw
 */
export function buildConnectionPath(
    source: PathSurface,
    target: PathSurface,
    bendpoints: readonly PathSurface[],
): string {
    const steps: PathSurface[] = [source, ...bendpoints, target];
    const legs: Leg[] = [];
    for (let index = 0; index + 1 < steps.length; index++) {
        legs.push(legBetween(steps[index], steps[index + 1]));
    }

    // The polyline: each leg's start, every leg's end, identical neighbours
    // collapsed (the bendpoints' shared surface point repeats).
    const points: [number, number][] = [];
    const push = (x: number, y: number): void => {
        const last = points.at(-1);
        if (last?.[0] !== x || last?.[1] !== y) {
            points.push([x, y]);
        }
    };
    for (const leg of legs) {
        push(leg.x1, leg.y1);
        push(leg.x2, leg.y2);
    }
    if (points.length < 2) {
        return "";
    }

    const [first, ...rest] = points;
    const segments = rest.map((point) => `L${point[0]},${point[1]}`);
    return `M${first[0]},${first[1]}${segments.join("")}`;
}
