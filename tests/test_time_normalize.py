"""_norm_time（フォーム時刻 → 24時間表記 HH:MM）の振る舞いテスト。"""

from app.main import _norm_time


def test_normalizes_to_24h_hh_mm() -> None:
    assert _norm_time("14:00") == "14:00"
    assert _norm_time("09:05") == "09:05"
    assert _norm_time("14:00:00") == "14:00"  # 秒は落とす


def test_empty_is_none() -> None:
    assert _norm_time("") is None


def test_invalid_is_none() -> None:
    assert _norm_time("2pm") is None
    assert _norm_time("25:00") is None
