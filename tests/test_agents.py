from app.agents.aggregation import detect_content_type


def test_detect_pdf_by_mime():
    assert detect_content_type("file.pdf", "application/pdf") == "documents"


def test_detect_docx_by_mime():
    mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert detect_content_type("file.docx", mime) == "documents"


def test_detect_image_by_mime():
    assert detect_content_type("photo.jpg", "image/jpeg") == "images"
    assert detect_content_type("photo.png", "image/png") == "images"


def test_detect_by_extension():
    assert detect_content_type("report.pdf", None) == "documents"
    assert detect_content_type("pic.png", None) == "images"
    assert detect_content_type("pic.webp", None) == "images"


def test_detect_unknown_falls_to_notes():
    assert detect_content_type("random.xyz", None) == "notes"
    assert detect_content_type(None, None) == "notes"
