from app.ml.pipeline import DefenseMLPipeline

_pipeline = DefenseMLPipeline()


def get_pipeline() -> DefenseMLPipeline:
    return _pipeline


def replace_pipeline(new_pipeline: DefenseMLPipeline) -> DefenseMLPipeline:
    global _pipeline
    _pipeline = new_pipeline
    return _pipeline
