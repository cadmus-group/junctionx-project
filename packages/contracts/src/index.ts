/**
 * GridTrace API & domain contracts.
 *
 * These types mirror the authoritative FastAPI Pydantic schemas. The canonical
 * source of truth is the FastAPI OpenAPI document; `pnpm generate:contracts`
 * exports it to `openapi.json` and emits `generated/openapi.ts`. The hand-stable
 * shared primitives below (GeoJSON, pagination, problem details) and the DTO
 * shapes are kept aligned with the backend and consumed by `@gridtrace/api-client`.
 */

export * from "./geojson";
export * from "./common";
export * from "./risk";
export * from "./assets";
export * from "./customers";
export * from "./dashboard";
export * from "./inspections";
export * from "./models";
