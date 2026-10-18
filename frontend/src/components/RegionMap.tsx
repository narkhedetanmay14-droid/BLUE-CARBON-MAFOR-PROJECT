import { useCallback, useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet-draw";
import { api } from "../services/api";

type Geometry = { type: "Polygon" | "MultiPolygon"; coordinates: unknown[] };
type Reference = { reference_id: string; district?: string; region?: string; total_mangrove_cover_km2?: string; assessment_year?: string; data_status?: string };
type ReferenceFeature = { type: "Feature"; id: string; geometry: Geometry; properties: Reference };
type ReferenceCollection = { type: "FeatureCollection"; features: ReferenceFeature[]; metadata?: { boundary_source?: string } };
type Selection = { referenceRegionId: string | null; referenceRegion?: Reference | null };

const yellowStyle: L.PathOptions = { color: "#b77900", weight: 2, fillColor: "#facc15", fillOpacity: 0.42 };
const redStyle: L.PathOptions = { color: "#b91c1c", weight: 3, fillColor: "#ef4444", fillOpacity: 0.46 };

function closeRing(points: L.LatLng[]) {
  return [...points, points[0]].map((point) => [point.lng, point.lat]);
}

export default function RegionMap({
  onChange,
  initialGeometry = null,
  initialReferenceRegionId = null,
  readOnly = false,
}: {
  onChange?: (geometry: Geometry | null, selection: Selection) => void;
  initialGeometry?: Geometry | null;
  initialReferenceRegionId?: string | null;
  readOnly?: boolean;
}) {
  const mapElementRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const referenceLayerRef = useRef<L.GeoJSON | null>(null);
  const selectedLayerRef = useRef<L.GeoJSON | null>(null);
  const customLayerRef = useRef<L.Polygon | null>(null);
  const customMarkersRef = useRef<L.Marker[]>([]);
  const previewRef = useRef<L.Polyline | null>(null);
  const geometryRef = useRef<Geometry | null>(initialGeometry);
  const selectionRef = useRef<Selection>({ referenceRegionId: initialReferenceRegionId, referenceRegion: null });
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;
  const [drawing, setDrawing] = useState(false);
  const [vertices, setVertices] = useState(0);
  const [referenceState, setReferenceState] = useState<"loading" | "ready" | "error">("loading");
  const [mapMessage, setMapMessage] = useState("Loading CSV-backed reference regions…");

  const emit = useCallback((geometry: Geometry | null, selection: Selection) => {
    geometryRef.current = geometry;
    selectionRef.current = selection;
    onChangeRef.current?.(geometry, selection);
  }, []);

  const clearCustomDrawing = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;
    customMarkersRef.current.forEach((marker) => map.removeLayer(marker));
    customMarkersRef.current = [];
    if (previewRef.current) map.removeLayer(previewRef.current);
    previewRef.current = null;
    if (customLayerRef.current) map.removeLayer(customLayerRef.current);
    customLayerRef.current = null;
    setVertices(0);
  }, []);

  const setReferenceStyles = useCallback((selectedId: string | null) => {
    referenceLayerRef.current?.eachLayer((layer) => {
      const feature = (layer as L.GeoJSON).feature as ReferenceFeature | undefined;
      if (feature) (layer as L.Path).setStyle(feature.id === selectedId ? redStyle : yellowStyle);
    });
  }, []);

  const showSavedGeometry = useCallback((geometry: Geometry, referenceId: string | null) => {
    const map = mapRef.current;
    if (!map) return;
    if (selectedLayerRef.current) map.removeLayer(selectedLayerRef.current);
    if (customLayerRef.current) map.removeLayer(customLayerRef.current);
    selectedLayerRef.current = L.geoJSON(geometry as GeoJSON.GeoJsonObject, { style: redStyle }).addTo(map);
    setReferenceStyles(referenceId);
    const bounds = selectedLayerRef.current.getBounds();
    if (bounds.isValid()) map.fitBounds(bounds.pad(0.12));
  }, [setReferenceStyles]);

  useEffect(() => {
    if (!mapElementRef.current || mapRef.current) return;
    const map = L.map(mapElementRef.current, { zoomControl: false }).setView([22.15, 88.75], 8);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "© OpenStreetMap contributors", maxZoom: 19 }).addTo(map);
    L.control.zoom({ position: "topright" }).addTo(map);
    const legend = new L.Control({ position: "bottomright" });
    legend.onAdd = () => {
      const node = L.DomUtil.create("div", "map-legend");
      node.innerHTML = '<strong>Map legend</strong><span><i class="legend-swatch yellow"></i>Yellow = CSV Reference Data Available</span><span><i class="legend-swatch red"></i>Red = User-Selected Project Region</span>';
      return node;
    };
    legend.addTo(map);
    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; };
  }, []);

  useEffect(() => {
    let active = true;
    api("/regions/reference-regions")
      .then((collection: ReferenceCollection) => {
        if (!active || !mapRef.current) return;
        const layer = L.geoJSON(collection as unknown as GeoJSON.GeoJsonObject, {
          style: yellowStyle,
          onEachFeature: (feature, layer) => {
            const selectedFeature = feature as ReferenceFeature;
            const props = selectedFeature.properties;
            layer.bindPopup(`<strong>${props.district || "Reference region"}</strong><br/>${props.region || ""}<br/>Mangrove cover: ${props.total_mangrove_cover_km2 || "Not available"} km²<br/>Assessment: ${props.assessment_year || "Not available"}<br/><small>${props.data_status || ""}</small>`);
            layer.on("click", () => {
              if (readOnly) return;
              clearCustomDrawing();
              if (selectedLayerRef.current && mapRef.current) mapRef.current.removeLayer(selectedLayerRef.current);
              selectedLayerRef.current = null;
              const selection = { referenceRegionId: selectedFeature.id, referenceRegion: selectedFeature.properties };
              emit(selectedFeature.geometry, selection);
              setReferenceStyles(selectedFeature.id);
              setDrawing(false);
              setMapMessage(`Selected ${selectedFeature.properties.district}. This project region is red.`);
            });
          },
        }).addTo(mapRef.current);
        referenceLayerRef.current = layer;
        const initialId = selectionRef.current.referenceRegionId;
        if (geometryRef.current) showSavedGeometry(geometryRef.current, initialId);
        else setReferenceStyles(initialId);
        setReferenceState("ready");
        setMapMessage(`${collection.features.length} CSV-backed regions are shown in yellow. Click one to select it.`);
      })
      .catch((error) => {
        if (!active) return;
        setReferenceState("error");
        setMapMessage(error instanceof Error ? error.message : "Reference regions could not be loaded.");
      });
    return () => { active = false; };
  }, [clearCustomDrawing, emit, readOnly, setReferenceStyles, showSavedGeometry]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !drawing || readOnly) return;
    const click = (event: L.LeafletMouseEvent) => {
      if ((event.originalEvent.target as HTMLElement).closest(".leaflet-control")) return;
      const marker = L.marker(event.latlng, { interactive: false, icon: L.divIcon({ className: "polygon-vertex-marker", html: `<div class="vertex-marker">${customMarkersRef.current.length + 1}</div>`, iconSize: [24, 24], iconAnchor: [12, 12] }) }).addTo(map);
      customMarkersRef.current.push(marker);
      const points = customMarkersRef.current.map((item) => item.getLatLng());
      if (previewRef.current) map.removeLayer(previewRef.current);
      if (points.length > 1) previewRef.current = L.polyline(points, { color: "#b91c1c", weight: 2, dashArray: "5, 5" }).addTo(map);
      setVertices(points.length);
    };
    map.on("click", click);
    return () => { map.off("click", click); };
  }, [drawing, readOnly]);

  const startDrawing = () => {
    clearCustomDrawing();
    if (selectedLayerRef.current && mapRef.current) mapRef.current.removeLayer(selectedLayerRef.current);
    selectedLayerRef.current = null;
    setReferenceStyles(null);
    emit(null, { referenceRegionId: null, referenceRegion: null });
    setDrawing(true);
    setMapMessage("Click at least three points on the map, then finish the polygon.");
  };
  const finishDrawing = () => {
    const points = customMarkersRef.current.map((marker) => marker.getLatLng());
    if (points.length < 3 || !mapRef.current) { setMapMessage("A project polygon needs at least three vertices."); return; }
    if (previewRef.current) mapRef.current.removeLayer(previewRef.current);
    previewRef.current = null;
    customLayerRef.current = L.polygon(points, redStyle).addTo(mapRef.current);
    emit({ type: "Polygon", coordinates: [closeRing(points)] }, { referenceRegionId: null, referenceRegion: null });
    setDrawing(false);
    setMapMessage("Custom project polygon selected in red.");
  };
  const undo = () => {
    const marker = customMarkersRef.current.pop();
    if (marker && mapRef.current) mapRef.current.removeLayer(marker);
    const points = customMarkersRef.current.map((item) => item.getLatLng());
    if (previewRef.current && mapRef.current) mapRef.current.removeLayer(previewRef.current);
    previewRef.current = points.length > 1 && mapRef.current ? L.polyline(points, { color: "#b91c1c", weight: 2, dashArray: "5, 5" }).addTo(mapRef.current) : null;
    setVertices(points.length);
  };
  const clear = () => {
    clearCustomDrawing();
    if (selectedLayerRef.current && mapRef.current) mapRef.current.removeLayer(selectedLayerRef.current);
    selectedLayerRef.current = null;
    setReferenceStyles(null);
    emit(null, { referenceRegionId: null, referenceRegion: null });
    setDrawing(false);
    setMapMessage("Selection cleared. CSV-backed reference regions remain yellow.");
  };

  return <div className="map-wrap">
    <div ref={mapElementRef} className="map-canvas" aria-label="Project region map" />
    {!readOnly && <div className="map-controls-overlay">
      {!drawing ? <button type="button" className="map-control-btn primary" onClick={startDrawing}>Draw custom region</button> : <><button type="button" className="map-control-btn success" onClick={finishDrawing} disabled={vertices < 3}>Finish polygon</button><button type="button" className="map-control-btn" onClick={undo} disabled={!vertices}>Undo point</button></>}
      <button type="button" className="map-control-btn danger" onClick={clear}>Clear selection</button>
    </div>}
    <p className={referenceState === "error" ? "map-message error" : "map-message"} role="status">{mapMessage}</p>
  </div>;
}
