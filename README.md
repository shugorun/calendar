# 未確定予定カレンダー

スクショ・写真・テキストから日付を抽出し、まだ確定していない予定としてカレンダーに表示する個人向けアプリ。
締切や日程の「見たけど忘れる／調べ直しが面倒」を解消する。

設計の語彙は [CONTEXT.md](./CONTEXT.md)、後戻りしにくい決定は [docs/adr/](./docs/adr/) を参照。

## 開発環境

- バックエンド（`app/`）: FastAPI の JSON API。Python 3.13 / [uv](https://docs.astral.sh/uv/) で venv 管理
- フロント（`web/`）: React 19 + TypeScript + Vite の SPA
- DB: SQLite（ファイル1つ）
- バック: Lint/Format = Ruff、型 = mypy（`strict`）
- フロント: Lint = ESLint、Format = Prettier、型 = tsc
- 構成の決定は [docs/adr/0005-react-spa-and-json-api.md](./docs/adr/0005-react-spa-and-json-api.md)

## セットアップ

```sh
uv sync                 # バックエンド: .venv を作成し依存をインストール
npm --prefix web install   # フロント: node_modules を作成
```

## 起動（dev は 2 プロセス）

```sh
# ターミナル1: API（FastAPI）
uv run uvicorn app.main:app --port 8000

# ターミナル2: 画面（Vite。/api を 8000 へプロキシ）
npm --prefix web run dev
# http://localhost:5173 を開く
```

## 検証（commit 前に緑にする）

```sh
# バックエンド
uv run pytest
uv run ruff check app tests
uv run ruff format --check app tests
uv run mypy app

# フロント
npm --prefix web run typecheck
npm --prefix web run lint
npm --prefix web run format:check
```
