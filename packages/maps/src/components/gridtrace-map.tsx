"use client";

import type { Layer } from "@deck.gl/core";
import { MapboxOverlay } from "@deck.gl/mapbox";
import { MAP_DEFAULTS } from "@gridtrace/config";
import maplibregl, { type Map as MapLibreMap, type StyleSpecification } from "maplibre-gl";
import { useEffect, useRef, type ReactNode } from "react";
import type { Bounds } from "../geometry";

export interface GridTraceMapProps {
  /** A style URL or an inline MapLibre style specification. */
  styleUrl: string | StyleSpecification;
  layers: Layer[];
  center?: [number, number];
  zoom?: number;
  minZoom?: number;
  maxZoom?: number;
  /** Fit to these bounds whenever they change. */
  fitBounds?: Bounds | null;
  interactive?: boolean;
  className?: string;
  children?: ReactNode;
  onLoad?: (map: MapLibreMap) => void;
}

export function GridTraceMap({
  styleUrl,
  layers,
  center = MAP_DEFAULTS.center,
  zoom = MAP_DEFAULTS.zoom,
  minZoom = MAP_DEFAULTS.minZoom,
  maxZoom = MAP_DEFAULTS.maxZoom,
  fitBounds,
  interactive = true,
  className,
  children,
  onLoad,
}: GridTraceMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: styleUrl,
      center,
      zoom,
      minZoom,
      maxZoom,
      interactive,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");

    const overlay = new MapboxOverlay({ interleaved: false, layers });
    map.addControl(overlay as unknown as maplibregl.IControl);
    overlayRef.current = overlay;
    mapRef.current = map;

    map.on("load", () => onLoad?.(map));

    return () => {
      overlay.finalize();
      map.remove();
      mapRef.current = null;
      overlayRef.current = null;
    };
    // Initialize once; subsequent prop changes are handled by dedicated effects.
  }, []);

  useEffect(() => {
    overlayRef.current?.setProps({ layers });
  }, [layers]);

  useEffect(() => {
    const map = mapRef.current;
    if (map && styleUrl) map.setStyle(styleUrl);
  }, [styleUrl]);

  useEffect(() => {
    const map = mapRef.current;
    if (map && fitBounds) {
      map.fitBounds(fitBounds, { padding: 64, maxZoom: 14, duration: 600 });
    }
  }, [fitBounds]);

  return (
    <div className={className ?? "relative h-full w-full"}>
      <div ref={containerRef} className="absolute inset-0 z-0" />
      {children ? (
        <div className="pointer-events-none absolute inset-0 z-10">{children}</div>
      ) : null}
    </div>
  );
}
