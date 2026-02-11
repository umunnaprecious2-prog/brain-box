from app.telegram.handlers import _has_publish_trigger


def test_trigger_with_hashtag():
    assert _has_publish_trigger("Check this out #github") is True


def test_trigger_case_insensitive():
    assert _has_publish_trigger("Share this #GitHub") is True
    assert _has_publish_trigger("#GITHUB post") is True


def test_trigger_at_start():
    assert _has_publish_trigger("#github some text") is True


def test_trigger_at_end():
    assert _has_publish_trigger("some text #github") is True


def test_no_trigger_without_hashtag():
    assert _has_publish_trigger("Just a normal note") is False


def test_no_trigger_github_without_hash():
    assert _has_publish_trigger("Push to github please") is False


def test_no_trigger_none():
    assert _has_publish_trigger(None) is False


def test_no_trigger_empty():
    assert _has_publish_trigger("") is False
