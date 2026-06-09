# フロントは React SPA、バックエンドは JSON API に分ける

画面（HTML/JS）は React + TypeScript の SPA（`web/`）が持ち、FastAPI（`app/`）は JSON を返す API に徹する。サーバー側で HTML を組み立てる Jinja テンプレートは廃止する。

## なぜ

- これまでは FastAPI + Jinja のサーバーレンダリング（フォーム POST → 303 リダイレクト）だった。デザインをゼロから作り直すにあたり、画面のマークアップを 1 か所（React）に集約したい。
- 「Python バックエンド＋React フロント」という素直な分担にすることで、UI の状態（編集中・確定の切替など）をクライアントで扱え、デザインの反復（HMR）が速くなる。
- ADR-0003「自前カレンダー UI を持つ」は維持する。本 ADR は *どう描くか*（MPA→SPA）を定めるもので、*自前で描く*方針は変えない。

## 決定

- **フロント**: React 19 + TypeScript + Vite（`web/`）。ルーティングは react-router-dom。
- **API**: FastAPI のエンドポイントは `/api/*` で JSON を返す（取得は GET、変更は POST、変更系は 204）。取り込みのみ multipart（画像）。
- **dev**: Vite dev サーバ（5173）が `/api` を uvicorn（8000）へプロキシ（同一オリジン扱いで CORS 不要）。HMR でデザイン反映が即時。
- **デザイン**: CSS はいったん全削除（ゼロから作り直す前提）。マークアップには意味のある class 名だけ残し、スタイルは未適用。

## Consequences

- ドメイン層（`app/repository.py` の dataclass）は FastAPI がそのまま JSON 化するため、API 化による変更は小さい。バックエンドのテストはドメイン層中心で影響なし。
- ビルド/起動が 2 プロセス（uvicorn + Vite）になる。`/.claude/launch.json` に `api` と `web` の 2 構成を用意。
- 本番配信（FastAPI が `web/dist` を配る等）は将来の課題。当面はローカル dev 前提。
- 不要になった `jinja2` 依存は削除した。
