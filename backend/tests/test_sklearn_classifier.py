import joblib
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.ai.classifier import KeywordTextClassifier
from app.ai.sklearn_classifier import SklearnTextClassifier
from app.api.deps import get_text_classifier
from app.core.enums import ComplaintCategory

TEXTS = ["big pothole on the road", "deep pothole and cracks", "traffic jam every evening", "long queue of cars jam"]
LABELS = ["Road Damage", "Road Damage", "Traffic Congestion", "Traffic Congestion"]


@pytest.fixture
def tiny_model(tmp_path):
    pipeline = Pipeline([("tfidf", TfidfVectorizer()), ("model", LogisticRegression())]).fit(TEXTS, LABELS)
    path = tmp_path / "tiny.joblib"
    joblib.dump(pipeline, path)
    return path


def test_loaded_model_returns_a_category_and_a_confidence(tiny_model):
    prediction = SklearnTextClassifier(tiny_model).predict("a pothole near the school")
    assert prediction.category == ComplaintCategory.ROAD_DAMAGE
    assert 0 < prediction.confidence <= 1


def test_the_trained_classifier_is_used_when_its_file_exists(settings, tiny_model):
    chosen = get_text_classifier(settings.model_copy(update={"text_classifier_path": tiny_model}))
    assert isinstance(chosen, SklearnTextClassifier)


def test_the_keyword_baseline_is_used_when_the_file_is_missing(settings, tmp_path):
    chosen = get_text_classifier(settings.model_copy(update={"text_classifier_path": tmp_path / "missing.joblib"}))
    assert isinstance(chosen, KeywordTextClassifier)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("There is a big pothole in the middle of the road", "Road Damage"),
        ("سڑک پر بہت بڑا گڑھا ہے", "Road Damage"),
        ("Railway phatak ka gate toota hua hai", "Railway Crossing"),
        ("Every evening there is a long traffic jam near the underpass", "Traffic Congestion"),
        ("The traffic signal at this chowk is not working", "Missing Traffic Control"),
        ("Garbage is piled up and the smell is unbearable", "Other"),
    ],
)
def test_the_shipped_model_handles_clear_examples_in_all_three_languages(settings, text, expected):
    assert settings.text_classifier_path.exists(), "run python -m ml.text.train_classifier"
    prediction = get_text_classifier(settings).predict(text)
    assert prediction.category.value == expected


def test_an_unreadable_model_file_falls_back_to_the_baseline(settings, tmp_path):
    broken = tmp_path / "broken.joblib"
    broken.write_bytes(b"this is not a model")
    chosen = get_text_classifier(settings.model_copy(update={"text_classifier_path": broken}))
    assert isinstance(chosen, KeywordTextClassifier)
