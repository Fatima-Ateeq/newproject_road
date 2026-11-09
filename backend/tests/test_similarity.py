from app.ai.similarity import jaccard


def test_identical_texts_are_fully_similar():
    assert jaccard("big pothole near school", "Big POTHOLE near school") == 1.0


def test_unrelated_texts_share_nothing():
    assert jaccard("big pothole near school", "street lights are off") == 0.0


def test_partial_overlap_is_between_zero_and_one():
    assert 0 < jaccard("deep pothole near the school gate", "pothole near the market") < 1


def test_urdu_text_is_compared_word_by_word():
    assert jaccard("سڑک پر بہت بڑا گڑھا ہے", "سڑک پر بڑا گڑھا ہے") > 0.5


def test_empty_text_has_zero_similarity():
    assert jaccard("", "anything here") == 0.0
