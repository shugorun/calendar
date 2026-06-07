"""抽出アダプタの組み立て（ADR-0002: プロバイダ差し替え可能）。"""

import os

from app.extraction.adapter import ExtractionAdapter
from app.extraction.dummy import DummyExtractor


def build_extractor() -> ExtractionAdapter:
    """環境変数に応じて抽出アダプタを選ぶ。鍵が無ければダミーに退避する。"""
    provider = os.environ.get("EXTRACTION_PROVIDER", "gemini").strip().lower()
    if provider == "gemini" and os.environ.get("GEMINI_API_KEY"):
        from app.extraction.gemini import GeminiExtractor

        return GeminiExtractor()
    return DummyExtractor()
