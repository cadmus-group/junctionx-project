# GIS layers

The map (`packages/maps` → `GridTraceMap`) uses **MapLibre GL JS** as the primary
engine, with **deck.gl** overlays for large point layers.

| Layer                  | Source/rendering |
|------------------------|------------------|
| Administrative boundaries | MapLibre GeoJSON/vector |
| Distribution lines     | MapLibre GeoJSON |
| Substations            | MapLibre GeoJSON |
| Transformers           | MapLibre GeoJSON |
| Customer points        | deck.gl ScatterplotLayer |
| H3 risk heatmap        | deck.gl / server hotspot aggregation |
| Transformer service areas | MapLibre fill |
| Inspection routes      | MapLibre line |

## Performance rules

- Do not render individual customers at national zoom (`customerDetailMinZoom`).
- Debounce viewport queries and **abort stale requests** (AbortController in the client).
- Memoize deck.gl layer definitions.
- Provide cached demo GeoJSON (`apps/web/public/demo/`) for offline mode.

## Coordinates

All geometry is SRID 4326 (WGS 84). GeoJSON is used for MVP map endpoints
(`/gis/anomalies/geojson`, `/gis/hotspots`).
