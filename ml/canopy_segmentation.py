class ModelUnavailable(RuntimeError): pass
def segment_canopy(image, model_path=None):
    raise ModelUnavailable("No validated canopy-segmentation model is configured.")
