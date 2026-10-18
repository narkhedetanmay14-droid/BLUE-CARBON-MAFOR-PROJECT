from app.services.geospatial_service import validate_polygon
def test_valid_polygon():
    g={"type":"Polygon","coordinates":[[[72.0,19.0],[72.01,19.0],[72.01,19.01],[72.0,19.01],[72.0,19.0]]]}
    result=validate_polygon(g)
    assert result["valid"] is True
    assert result["area_hectares"] > 0
def test_open_ring_rejected():
    g={"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,1]]]}
    assert validate_polygon(g)["valid"] is False
def test_wrong_type_rejected():
    assert validate_polygon({"type":"Point","coordinates":[0,0]})["valid"] is False
