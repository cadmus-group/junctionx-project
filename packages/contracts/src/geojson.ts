/** Minimal RFC 7946 GeoJSON types (SRID 4326 / WGS 84). */

export type Position = [number, number] | [number, number, number];

export interface Point {
  type: "Point";
  coordinates: Position;
}
export interface LineString {
  type: "LineString";
  coordinates: Position[];
}
export interface Polygon {
  type: "Polygon";
  coordinates: Position[][];
}
export interface MultiPolygon {
  type: "MultiPolygon";
  coordinates: Position[][][];
}

export type Geometry = Point | LineString | Polygon | MultiPolygon;

export interface Feature<G extends Geometry = Geometry, P = Record<string, unknown>> {
  type: "Feature";
  geometry: G;
  properties: P;
  id?: string | number;
}

export interface FeatureCollection<G extends Geometry = Geometry, P = Record<string, unknown>> {
  type: "FeatureCollection";
  features: Feature<G, P>[];
  bbox?: [number, number, number, number];
}

export interface BoundingBox {
  min_lon: number;
  min_lat: number;
  max_lon: number;
  max_lat: number;
}
