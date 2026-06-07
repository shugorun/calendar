"""build_input（取り込みフォームの値 → 元入力）の振る舞いテスト。"""

from app.extraction import build_input


def test_image_keeps_text_as_context() -> None:
    # 画像と一緒に添えたテキストは捨てずヒントとして保持する。
    src = build_input("PACLIC", b"\x89PNG-bytes", "image/jpeg")
    assert src is not None
    assert src.kind == "image"
    assert src.image == b"\x89PNG-bytes"
    assert src.image_mime == "image/jpeg"
    assert src.text == "PACLIC"


def test_text_used_when_no_image() -> None:
    src = build_input("応募締切 6/30", None, None)
    assert src is not None
    assert src.kind == "text"
    assert src.text == "応募締切 6/30"


def test_empty_input_returns_none() -> None:
    assert build_input("   ", None, None) is None
    assert build_input("", None, None) is None


def test_image_defaults_mime_when_missing() -> None:
    src = build_input("", b"data", None)
    assert src is not None
    assert src.image_mime == "image/png"
    assert src.text is None  # 空テキストは保持しない
