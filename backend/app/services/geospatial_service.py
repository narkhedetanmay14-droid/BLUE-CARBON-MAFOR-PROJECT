def validate_polygon(geojson: dict) -> dict:
    try:
        if geojson.get("type") == "Feature":
            geom = geojson.get("geometry") or {}
        else:
            geom = geojson
        if geom.get("type") not in {"Polygon", "MultiPolygon"}:
            return {"valid":False,"error":"A GeoJSON Polygon or MultiPolygon is required"}
        polygons = [geom.get("coordinates")] if geom.get("type") == "Polygon" else geom.get("coordinates")
        if not polygons or not all(polygon and polygon[0] and len(polygon[0]) >= 4 for polygon in polygons):
            return {"valid":False,"error":"Each polygon needs at least three vertices and a closing point"}
        for polygon in polygons:
            for ring in polygon:
                if ring[0] != ring[-1]:
                    return {"valid":False,"error":"Polygon rings must be closed"}
                for pt in ring:
                    if len(pt)<2 or not (-180 <= float(pt[0]) <= 180) or not (-90 <= float(pt[1]) <= 90):
                        return {"valid":False,"error":"Invalid longitude/latitude coordinate"}
        try:
            from shapely.geometry import shape
            from pyproj import CRS, Transformer
            from shapely.ops import transform
            from shapely.validation import explain_validity
            poly=shape(geom)
            if not poly.is_valid or poly.area == 0:
                return {"valid":False,"error":"Invalid polygon: "+explain_validity(poly)}
            lon,lat=poly.centroid.x,poly.centroid.y
            zone=int((lon+180)//6)+1
            epsg=(32600+zone) if lat>=0 else (32700+zone)
            transformer=Transformer.from_crs("EPSG:4326",CRS.from_epsg(epsg),always_xy=True)
            area=transform(transformer.transform,poly).area/10000
            return {"valid":True,"area_hectares":round(area,6),"area_method":f"UTM EPSG:{epsg}"}
        except ImportError:
            # Fallback is deliberately approximate; do not claim geodesic-grade accuracy.
            import math
            rings = [ring for polygon in polygons for ring in polygon]
            points = [point for ring in rings for point in ring[:-1]]
            lat0=sum(float(p[1]) for p in points)/max(1,len(points))
            def ring_area(ring):
                xy=[(math.radians(float(x))*6371008.8*math.cos(math.radians(lat0)),math.radians(float(y))*6371008.8) for x,y,*_ in ring]
                return abs(sum(xy[i][0]*xy[i+1][1]-xy[i+1][0]*xy[i][1] for i in range(len(xy)-1)))/2
            area=sum(ring_area(ring) for polygon in polygons for ring in polygon)
            return {"valid":True,"area_hectares":round(area/10000,6),"area_method":"spherical approximation fallback"}
    except Exception as exc:
        return {"valid":False,"error":f"Could not validate polygon: {exc}"}
