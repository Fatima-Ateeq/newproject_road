"""Loads the trained text classifier saved by `python -m ml.text.train_classifier`."""

from functools import lru_cache
from pathlib import Path

import joblib

from app.ai.classifier import Prediction
from app.core.enums import ComplaintCategory


class SklearnTextClassifier:
    """Only load model files that our own training script produced. A pickle can run code when opened."""

    def __init__(self, model_path: Path) -> None:
        self._pipeline = joblib.load(model_path)

    def predict(self, text: str) -> Prediction:
        probabilities = self._pipeline.predict_proba([text])[0]
        best = int(probabilities.argmax())
        return Prediction(ComplaintCategory(self._pipeline.classes_[best]), float(probabilities[best]))


@lru_cache
def load_classifier(model_path: Path) -> SklearnTextClassifier:
    """Loading takes a moment, so it happens once per process."""
    return SklearnTextClassifier(model_path)
