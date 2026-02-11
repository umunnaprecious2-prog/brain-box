from app.storage.file_storage import _build_filename, _sanitize_filename, save_file


def test_sanitize_filename_removes_special_chars():
    assert _sanitize_filename("file<name>:test?.txt") == "file_name__test_.txt"


def test_sanitize_filename_empty_returns_unnamed():
    assert _sanitize_filename("...") == "unnamed"


def test_build_filename_contains_message_id():
    result = _build_filename(42, "test.pdf")
    assert "_42_" in result
    assert "test.pdf" in result


def test_save_file_creates_file(tmp_storage):
    import app.config.settings as cfg_mod
    import app.storage.file_storage as fs_mod
    from app.storage.file_storage import init_storage

    original_path = cfg_mod.STORAGE_BASE_PATH
    cfg_mod.STORAGE_BASE_PATH = tmp_storage
    fs_mod.STORAGE_BASE_PATH = tmp_storage

    try:
        init_storage()
        path = save_file(
            content_type="notes",
            topic="test_topic",
            telegram_message_id=1,
            original_name="hello.txt",
            data=b"Hello World",
        )
        assert path.exists()
        assert path.read_bytes() == b"Hello World"
        assert "notes" in str(path)
        assert "test_topic" in str(path)
    finally:
        cfg_mod.STORAGE_BASE_PATH = original_path


def test_save_file_rejects_invalid_content_type(tmp_storage):
    import pytest

    import app.config.settings as cfg_mod
    import app.storage.file_storage as fs_mod

    cfg_mod.STORAGE_BASE_PATH = tmp_storage
    fs_mod.STORAGE_BASE_PATH = tmp_storage

    with pytest.raises(ValueError, match="Unknown content type"):
        save_file(
            content_type="videos",
            topic="test",
            telegram_message_id=1,
            original_name="test.mp4",
            data=b"data",
        )
