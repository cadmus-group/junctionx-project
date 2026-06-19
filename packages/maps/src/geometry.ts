import type {
  Feature,
  FeatureCollection,
  Geometry,
  Position,
} from "@gridtrace/contracts";

export type Bounds = [[number, number], [number, number]];

function eachPosition(coords: unknown, fn: (pos: Position) => void): void {
  if (!Array.isArray(coords)) return;
  if (typeof coords[0] === "number" && typeof coords[1] === "number") {
    fn(coords as Position);
    return;
  }
  for (const child of coords) eachPosition(child, fn);
}

/** Compute a [[west, south], [east, north]] bounding box for a geometry/collection. */
export function fitBoundsToGeometry(
  input: Geometry | Feature | FeatureCollection | null | undefined
): Bounds | null {
  if (!input) return null;

  let minLon = Infinity;
  let minLat = Infinity;
  let maxLon = -Infinity;
  let maxLat = -Infinity;

  const visit = (geometry: Geometry) => {
    eachPosition(geometry.coordinates, ([lon, lat]) => {
      if (lon < minLon) minLon = lon;
      if (lat < minLat) minLat = lat;
      if (lon > maxLon) maxLon = lon;
      if (lat > maxLat) maxLat = lat;
    });
  };

  if (input.type === "FeatureCollection") {
    for (const f of input.features) visit(f.geometry);
  } else if (input.type === "Feature") {
    visit(input.geometry);
  } else {
    visit(input);
  }

  if (!Number.isFinite(minLon) || !Number.isFinite(minLat)) return null;
  return [
    [minLon, minLat],
    [maxLon, maxLat],
  ];
}

export function boundsCenter(bounds: Bounds): [number, number] {
  return [(bounds[0][0] + bounds[1][0]) / 2, (bounds[0][1] + bounds[1][1]) / 2];
}
