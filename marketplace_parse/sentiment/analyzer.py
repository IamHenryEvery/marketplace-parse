from threading import Lock
from typing import Any

from transformers import pipeline

from marketplace_parse.db.enums import SentimentLabel


MODEL_NAME = "blanchefort/rubert-base-cased-sentiment"
MAX_LENGTH = 512
BATCH_SIZE = 16

_LABEL_MAP = {
    "POSITIVE": SentimentLabel.positive,
    "NEGATIVE": SentimentLabel.negative,
    "NEUTRAL": SentimentLabel.neutral,
}

_pipeline: Any | None = None
_pipeline_lock = Lock()


def _get_pipeline():
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    with _pipeline_lock:
        if _pipeline is None:
            _pipeline = pipeline(  # pyright: ignore[reportCallIssue]
                "sentiment-analysis",
                model=MODEL_NAME,
                tokenizer=MODEL_NAME,
                device=-1,
            )
    return _pipeline


def analyze(texts: list[str]) -> list[tuple[SentimentLabel, float]]:
    """Run sentiment classification on a batch of texts.

    Returns list aligned with input: (label, signed_score). The signed score
    is in [-1, 1]: positive class → +confidence, negative class → -confidence,
    neutral → 0.0. Suitable for averaging across reviews.
    """
    if not texts:
        return []
    pipe = _get_pipeline()
    raw = pipe(texts, truncation=True, max_length=MAX_LENGTH, batch_size=BATCH_SIZE)
    out: list[tuple[SentimentLabel, float]] = []
    for r in raw:
        label = _LABEL_MAP[r["label"]]
        score = float(r["score"])
        if label is SentimentLabel.positive:
            signed = score
        elif label is SentimentLabel.negative:
            signed = -score
        else:
            signed = 0.0
        out.append((label, signed))
    return out
