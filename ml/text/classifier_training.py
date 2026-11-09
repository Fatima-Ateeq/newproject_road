"""Training and measuring the complaint text classifier. Pure functions, no files read or written here."""

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import FeatureUnion, Pipeline

from app.ai.classifier import KeywordTextClassifier
from ml.common.categories import CATEGORIES


@dataclass(frozen=True)
class Metrics:
    examples: int
    accuracy: float
    macro_f1: float
    f1_per_category: dict[str, float]


def build_pipeline() -> Pipeline:
    """Word and character n-gram TF-IDF features feeding a logistic regression.

    Character n-grams matter here: Roman Urdu has no fixed spelling ('gaddha', 'gadha', 'gadda'),
    and character pieces still overlap when whole words do not. Only scikit-learn parts are used,
    so the saved file loads anywhere with the same scikit-learn version and needs none of our code.
    """
    features = FeatureUnion(
        [
            ("words", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True)),
            ("chars", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True)),
        ]
    )
    model = LogisticRegression(C=10, max_iter=2000, class_weight="balanced")
    return Pipeline([("features", features), ("model", model)])


def _texts_and_labels(rows: list[dict[str, str]]) -> tuple[list[str], list[str]]:
    return [row["text"] for row in rows], [row["label"] for row in rows]


def score(true_labels: list[str], predicted: list[str]) -> Metrics:
    per_category = f1_score(true_labels, predicted, labels=CATEGORIES, average=None, zero_division=0)
    return Metrics(
        examples=len(true_labels),
        accuracy=float(accuracy_score(true_labels, predicted)),
        macro_f1=float(f1_score(true_labels, predicted, labels=CATEGORIES, average="macro", zero_division=0)),
        f1_per_category=dict(zip(CATEGORIES, (float(value) for value in per_category))),
    )


def cross_validated_metrics(rows: list[dict[str, str]], folds: int = 5, seed: int = 42) -> Metrics:
    """Every example is predicted by a model that never saw it. More stable than one small validation set."""
    texts, labels = _texts_and_labels(rows)
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    predicted = cross_val_predict(build_pipeline(), texts, labels, cv=splitter)
    return score(labels, list(predicted))


def validation_metrics(train_rows: list[dict[str, str]], val_rows: list[dict[str, str]]) -> Metrics:
    train_texts, train_labels = _texts_and_labels(train_rows)
    val_texts, val_labels = _texts_and_labels(val_rows)
    pipeline = build_pipeline().fit(train_texts, train_labels)
    return score(val_labels, list(pipeline.predict(val_texts)))


def baseline_metrics(rows: list[dict[str, str]]) -> Metrics:
    """The keyword baseline needs no training, so it is simply scored on the same examples."""
    texts, labels = _texts_and_labels(rows)
    classifier = KeywordTextClassifier()
    return score(labels, [classifier.predict(text).category.value for text in texts])


def fit_final_model(rows: list[dict[str, str]]) -> Pipeline:
    texts, labels = _texts_and_labels(rows)
    return build_pipeline().fit(texts, labels)
