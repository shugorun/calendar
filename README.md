# 未確定予定カレンダー

スクショ・写真・テキストから日付を抽出し、まだ確定していない予定としてカレンダーに表示する個人向けアプリ。
締切や日程の「見たけど忘れる／調べ直しが面倒」を解消する。

設計の語彙は [CONTEXT.md](./CONTEXT.md)、後戻りしにくい決定は [docs/adr/](./docs/adr/) を参照。

## 開発環境

- Python 3.13 / [uv](https://docs.astral.sh/uv/) でプロジェクト専用 venv を管理
- バックエンド: FastAPI（localhost で起動する小さなローカルサーバー）
- DB: SQLite（ファイル1つ）
- フロント: Jinja2 テンプレ＋素の JS（軽量）
- Lint/Format: Ruff、型: mypy（`strict`）

## セットアップ

```sh
uv sync                 # .venv を作成し依存をインストール
```

## 起動

```sh
uv run uvicorn app.main:app --reload
# http://127.0.0.1:8000 を開く
```

## 検証（commit 前に緑にする）

```sh
uv run pytest
uv run ruff check app tests
uv run ruff format --check app tests
uv run mypy app
```
