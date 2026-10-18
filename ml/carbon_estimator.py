def estimate_carbon(*, ecosystem_type, canopy_area_hectares=None, species_coefficients=None, annual_rate=None):
    if not species_coefficients or canopy_area_hectares is None:
        return {"status":"unavailable","carbon_stock_tco2e":None,"annual_sequestration_tco2e_per_year":None,"reason":"Validated ecosystem-specific coefficients and measured input data are required."}
    raise NotImplementedError("Provide a documented, sourced methodology and uncertainty model before enabling estimates.")
