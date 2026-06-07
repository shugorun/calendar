"""抽出アダプタの組み立て（ADR-0002: プロバイダ差し替え可能）。"""

import os

from app.extraction.adapter import ExtractionAdapter, ExtractionInput
from app.extraction.dummy import DummyExtractor


def build_extractor() -> ExtractionAdapter:
    """環境変数に応じて抽出アダプタを選ぶ。鍵が無ければダミーに退避する。"""
    provider = (os.environ.get("EXTRACTION_PROVIDER") or "gemini").strip().lower()
    if provider == "gemini" and os.environ.get("GEMINI_API_KEY"):
        from app.extraction.gemini import GeminiExtractor

        return GeminiExtractor()
    return DummyExtractor()


def build_input(
    text: str, image: bytes | None, image_mime: str | None
) -> ExtractionInput | None:
    """取り込みフォームの値から元入力を作る。画像があれば優先。何も無ければ None。"""
    if image:
        return ExtractionInput(
            kind="image", image=image, image_mime=image_mime or "image/png"
        )
    if text.strip():
        return ExtractionInput(kind="text", text=text)
    return None
