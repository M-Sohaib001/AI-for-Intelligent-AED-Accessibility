"use client";

import { useEffect, useRef } from "react";
import type { Coordinate } from "@/types";

// ---------------------------------------------------------------------------
// RouteMap – renders a Leaflet map with the selected AED's walking route.
//
// Accepts `coordinates` as [lon, lat] pairs directly from /rank_aeds response.
// Converts to Leaflet's [lat, lon] format internally.
//
// OSM attribution is REQUIRED by licence – never remove it.
// ---------------------------------------------------------------------------

interface RouteMapProps {
  coordinates: Coordinate[]; // [lon, lat] pairs from Ayan's API
  facilityName: string;
}

export default function RouteMap({ coordinates, facilityName }: RouteMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<unknown>(null);

  useEffect(() => {
    if (!mapRef.current || !coordinates?.length) return;

    // Destroy previous map instance on re-render (e.g. user selects different AED)
    if (mapInstanceRef.current) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mapInstanceRef.current as any).remove();
      mapInstanceRef.current = null;
    }

    const injectLeaflet = async () => {
      if (!document.getElementById("leaflet-css")) {
        const link = document.createElement("link");
        link.id = "leaflet-css";
        link.rel = "stylesheet";
        link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
        document.head.appendChild(link);
      }

      if (!window.L) {
        await new Promise<void>((resolve, reject) => {
          const script = document.createElement("script");
          script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
          script.onload = () => resolve();
          script.onerror = reject;
          document.head.appendChild(script);
        });
      }

      const L = window.L;

      // Convert [lon, lat] → [lat, lon] for Leaflet
      const latLngs: [number, number][] = coordinates.map(
        ([lon, lat]) => [lat, lon]
      );

      const map = L.map(mapRef.current!, { zoomControl: true });
      mapInstanceRef.current = map;

      // OSM tile layer – attribution REQUIRED by OpenStreetMap licence
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution:
          '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map);

      // Walking route polyline (blue as per Ayan's spec)
      const polyline = L.polyline(latLngs, {
        color: "#6366f1",
        weight: 5,
        opacity: 0.85,
      }).addTo(map);

      // Start marker – user's location (first coordinate)
      L.circleMarker(latLngs[0], {
        radius: 9,
        color: "#22c55e",
        fillColor: "#22c55e",
        fillOpacity: 1,
        weight: 2,
      })
        .addTo(map)
        .bindTooltip("Your location", { permanent: false });

      // End marker – AED location (last coordinate)
      const endLatLng = latLngs[latLngs.length - 1];
      L.marker(endLatLng)
        .addTo(map)
        .bindTooltip(facilityName, { permanent: true, direction: "top" });

      // Fit map to route bounds
      map.fitBounds(polyline.getBounds(), { padding: [32, 32] });
    };

    injectLeaflet().catch(console.error);

    return () => {
      if (mapInstanceRef.current) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (mapInstanceRef.current as any).remove();
        mapInstanceRef.current = null;
      }
    };
  }, [coordinates, facilityName]);

  return (
    <div className="route-map-wrapper" id="route-map">
      <div
        ref={mapRef}
        className="route-map-canvas"
        aria-label={`Walking route to ${facilityName}`}
      />
    </div>
  );
}

declare global {
  interface Window {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    L: any;
  }
}
