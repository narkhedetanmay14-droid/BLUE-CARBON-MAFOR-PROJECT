def validate_image_metadata(metadata: dict):
    if not metadata.get("crs"): raise ValueError("A georeferenced image is required")
    if metadata.get("count",0)<1: raise ValueError("Image has no bands")
    return metadata
