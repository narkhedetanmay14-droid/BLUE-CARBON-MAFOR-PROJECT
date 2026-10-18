def count_detections(detections, polygon=None):
    if detections is None: raise ValueError("Detections are required")
    # Caller must supply only validated detections already filtered to the project polygon.
    return len(detections)
