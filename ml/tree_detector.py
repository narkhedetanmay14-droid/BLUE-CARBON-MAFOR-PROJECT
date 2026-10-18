class ModelUnavailable(RuntimeError): pass
def detect_trees(image, model_path=None):
    raise ModelUnavailable("No validated, licensed tree detector and model weights are configured. No predictions were generated.")
