import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from ml.carbon_estimator import estimate_carbon
def test_missing_inputs_unavailable():
    result=estimate_carbon(ecosystem_type="mangrove")
    assert result["status"]=="unavailable"
    assert result["carbon_stock_tco2e"] is None
