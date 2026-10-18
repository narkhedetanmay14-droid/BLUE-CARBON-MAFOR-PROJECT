import { useEffect, useRef, useState, useCallback } from "react";
import L from "leaflet";
import "leaflet-draw";

type DrawingState = "idle" | "drawing" | "finished";

export default function RegionMap({ onChange }: { onChange: (g: any) => void }) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const drawnItemsRef = useRef<L.FeatureGroup | null>(null);
  const currentPolygonRef = useRef<L.Polygon | null>(null);
  const markersRef = useRef<L.Marker[]>([]);
  const tempLineRef = useRef<L.Polyline | null>(null);
  const changeCallbackRef = useRef(onChange);
  
  changeCallbackRef.current = onChange;

  const [drawingState, setDrawingState] = useState<DrawingState>("idle");
  const [vertexCount, setVertexCount] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [areaHectares, setAreaHectares] = useState<number | null>(null);

  // Clear all markers
  const clearMarkers = useCallback(() => {
    markersRef.current.forEach((marker) => {
      if (mapInstanceRef.current) mapInstanceRef.current.removeLayer(marker);
    });
    markersRef.current = [];
  }, []);

  // Clear temporary line
  const clearTempLine = useCallback(() => {
    if (tempLineRef.current && mapInstanceRef.current) {
      mapInstanceRef.current.removeLayer(tempLineRef.current);
      tempLineRef.current = null;
    }
  }, []);

  // Remove current polygon
  const removeCurrentPolygon = useCallback(() => {
    if (currentPolygonRef.current && drawnItemsRef.current) {
      drawnItemsRef.current.removeLayer(currentPolygonRef.current);
      currentPolygonRef.current = null;
    }
  }, []);

  // Add a vertex marker
  const addMarker = useCallback((latlng: L.LatLng, index: number) => {
    if (!mapInstanceRef.current) return;
    
    const icon = L.divIcon({
      className: "polygon-vertex-marker",
      html: `<div class="vertex-marker" data-index="${index}">${index + 1}</div>`,
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });

    const marker = L.marker(latlng, { icon, interactive: false });
    marker.addTo(mapInstanceRef.current);
    markersRef.current.push(marker);
  }, []);

  // Update polygon preview from points
  const updatePolygonPreview = useCallback((points: L.LatLng[]) => {
    if (!mapInstanceRef.current || points.length < 2) return;

    clearTempLine();

    // Draw temporary line connecting all points
    tempLineRef.current = L.polyline(points, {
      color: "#2563eb",
      weight: 2,
      dashArray: "5, 5",
      opacity: 0.8,
    }).addTo(mapInstanceRef.current);
  }, [clearTempLine]);

  // Finish polygon by closing it
  const finishPolygon = useCallback(() => {
    const points = markersRef.current.map((m) => m.getLatLng());
    
    if (points.length < 3) {
      setErrorMessage("Polygon requires at least 3 vertices. Add more points.");
      return;
    }

    if (!mapInstanceRef.current || !drawnItemsRef.current) return;

    clearTempLine();
    removeCurrentPolygon();

    // Close the polygon by repeating first point at end
    const closedPoints = [...points, points[0]];

    // Create closed polygon
    currentPolygonRef.current = L.polygon(points, {
      color: "#059669",
      weight: 3,
      fillColor: "#10b981",
      fillOpacity: 0.25,
    });

    drawnItemsRef.current.addLayer(currentPolygonRef.current);

    // Generate GeoJSON with closed ring
    const coordinates = closedPoints.map((p) => [p.lng, p.lat]);
    const geojson = {
      type: "Polygon",
      coordinates: [coordinates],
    };

    changeCallbackRef.current(geojson);
    setDrawingState("finished");
    setVertexCount(points.length);
    setErrorMessage(null);

    // Calculate approximate area for display
    calculateArea(points);
  }, [clearTempLine, removeCurrentPolygon]);

  // Calculate area using spherical formula
  const calculateArea = (points: L.LatLng[]) => {
    if (points.length < 3) return;

    const R = 6371008.8; // Earth radius in meters
    const n = points.length;

    let area = 0;
    for (let i = 0; i < n; i++) {
      const j = (i + 1) % n;
      area += (points[i].lng * Math.PI) / 180 * (points[j].lat * Math.PI) / 180;
      area -= (points[j].lng * Math.PI) / 180 * (points[i].lat * Math.PI) / 180;
    }

    area = Math.abs(area * R * R / 2);
    setAreaHectares(Math.round((area / 10000) * 100) / 100);
  };

  // Initialize map
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;

    const map = L.map(mapRef.current).setView([19.076, 72.8777], 8);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 19,
    }).addTo(map);

    const drawnItems = new L.FeatureGroup();
    map.addLayer(drawnItems);

    // Position zoom controls in upper-right to avoid conflict with drawing controls
    L.control.zoom({
      position: "topright",
    }).addTo(map);

    mapInstanceRef.current = map;
    drawnItemsRef.current = drawnItems;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
      drawnItemsRef.current = null;
    };
  }, []);

  // Handle map clicks during drawing
  useEffect(() => {
    if (!mapInstanceRef.current || drawingState !== "drawing") return;

    const map = mapInstanceRef.current;

    const handleClick = (e: L.LeafletMouseEvent) => {
      // Prevent adding points when clicking on controls
      if ((e.originalEvent.target as HTMLElement).closest(".leaflet-control")) {
        return;
      }

      const latlng = e.latlng;
      
      // Add marker for the new vertex
      addMarker(latlng, markersRef.current.length);
      setVertexCount(markersRef.current.length);

      // Update preview line
      const points = markersRef.current.map((m) => m.getLatLng());
      updatePolygonPreview(points);

      setErrorMessage(null);
    };

    map.on("click", handleClick);

    return () => {
      map.off("click", handleClick);
    };
  }, [drawingState, addMarker, updatePolygonPreview]);

  // Start drawing
  const startDrawing = () => {
    clearMarkers();
    clearTempLine();
    removeCurrentPolygon();
    setDrawingState("drawing");
    setVertexCount(0);
    setErrorMessage(null);
    setAreaHectares(null);
    changeCallbackRef.current(null);
  };

  // Undo last point
  const undoLastPoint = () => {
    if (markersRef.current.length === 0) return;

    const lastMarker = markersRef.current.pop();
    if (lastMarker && mapInstanceRef.current) {
      mapInstanceRef.current.removeLayer(lastMarker);
    }

    setVertexCount(markersRef.current.length);

    if (markersRef.current.length >= 2) {
      const points = markersRef.current.map((m) => m.getLatLng());
      updatePolygonPreview(points);
    } else {
      clearTempLine();
    }
  };

  // Clear polygon
  const clearPolygon = () => {
    clearMarkers();
    clearTempLine();
    removeCurrentPolygon();
    setDrawingState("idle");
    setVertexCount(0);
    setErrorMessage(null);
    setAreaHectares(null);
    changeCallbackRef.current(null);
  };

  // Cancel drawing
  const cancelDrawing = () => {
    clearPolygon();
  };

  // Enable edit mode
  const editBoundary = () => {
    if (!currentPolygonRef.current || !mapInstanceRef.current) return;

    // Enable Leaflet.Draw edit mode
    const editHandler = new (L.Draw as any).Edit.Polygon(currentPolygonRef.current, {
      moveMarkers: false,
    });

    editHandler.enable();

    // Save changes on edit complete
    currentPolygonRef.current.on("edit", () => {
      const points = currentPolygonRef.current!.getLatLngs()[0] as L.LatLng[];
      const closedPoints = [...points, points[0]];
      const coordinates = closedPoints.map((p) => [p.lng, p.lat]);

      const geojson = {
        type: "Polygon",
        coordinates: [coordinates],
      };

      changeCallbackRef.current(geojson);
      setVertexCount(points.length);
      calculateArea(points);
    });
  };

  const canFinish = drawingState === "drawing" && vertexCount >= 3;
  const canUndo = drawingState === "drawing" && vertexCount > 0;
  const canEdit = drawingState === "finished";

  return (
    <div className="map-wrap">
      <div ref={mapRef} className="map-canvas" />

      {/* Drawing controls overlay */}
      <div className="map-controls-overlay">
        {drawingState === "idle" && (
          <button className="map-control-btn primary" onClick={startDrawing}>
            📍 Start Drawing
          </button>
        )}

        {drawingState === "drawing" && (
          <>
            <button
              className="map-control-btn success"
              onClick={finishPolygon}
              disabled={!canFinish}
              title={canFinish ? "Close the polygon and save" : "Add at least 3 vertices"}
            >
              ✓ Finish Polygon
            </button>
            <button
              className="map-control-btn"
              onClick={undoLastPoint}
              disabled={!canUndo}
            >
              ↩ Undo Last Point
            </button>
            <button className="map-control-btn danger" onClick={cancelDrawing}>
              ✕ Cancel Drawing
            </button>
          </>
        )}

        {drawingState === "finished" && (
          <>
            <button className="map-control-btn" onClick={editBoundary} disabled={!canEdit}>
              ✏ Edit Boundary
            </button>
            <button className="map-control-btn danger" onClick={clearPolygon}>
              🗑 Clear Polygon
            </button>
          </>
        )}
      </div>

      {/* Status display */}
      <div className="map-status-overlay">
        {drawingState === "drawing" && (
          <div className="status-info">
            <span className="vertex-count">
              Vertices: <strong>{vertexCount}</strong>
            </span>
            {vertexCount < 3 && (
              <span className="hint">Click to add {3 - vertexCount} more point(s)</span>
            )}
            {vertexCount >= 3 && (
              <span className="hint ready">Click "Finish Polygon" to close</span>
            )}
          </div>
        )}

        {drawingState === "finished" && (
          <div className="status-info success">
            <span className="vertex-count">
              Polygon: <strong>{vertexCount}</strong> vertices
            </span>
            {areaHectares !== null && (
              <span className="area-display">
                Area: <strong>{areaHectares.toLocaleString()}</strong> ha
              </span>
            )}
          </div>
        )}

        {errorMessage && <div className="status-error">{errorMessage}</div>}
      </div>

      {/* Help text */}
      <p className="map-help">
        {drawingState === "idle" && "Click \"Start Drawing\" to begin defining a region boundary."}
        {drawingState === "drawing" && "Click on the map to add boundary points. Minimum 3 points required."}
        {drawingState === "finished" && "Polygon closed and validated. Submit the form to register this region."}
      </p>
    </div>
  );
}
