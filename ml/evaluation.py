def summarize_metrics(*, precision=None, recall=None, f1=None, validation_dataset=None):
    if validation_dataset is None:
        return {"status":"unvalidated","precision":None,"recall":None,"f1":None,"reason":"A labelled validation dataset is required."}
    return {"status":"reported","precision":precision,"recall":recall,"f1":f1,"validation_dataset":validation_dataset}
