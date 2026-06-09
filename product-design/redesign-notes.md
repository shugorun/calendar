# 改修案ノート（2026-06 のUI課題）

実利用で出た課題をグリルで仕分けた結果のうち、**UIに回す5件**の設計メモ。
ビジュアルは [`minimal-component.html`](./minimal-component.html) の `#redesign` セクション、
スタイルは [`minimal-component.css`](./minimal-component.css) の「▼ 改修案」ブロックに 1:1 で入れてある。
ここはその**意図と、web/ 移植・バックエンドの申し送り**を残す。

語彙は [../CONTEXT.md](../CONTEXT.md) を正とする（日時未定＝日付が無い／読み取れない、目安＝必ず日付を伴う属性）。

> 抽出・再取得まわり（日付なし→未定、不正日付→未定、取り込み後の即時表示）は
> 既にコードで対応済み。本ノートは**残りのUI**だけを扱う。

---

## ① 写真を付けたときレイアウトが跳ねる → 滑らかに開く

- **症状**: `.intake-thumbs` が条件描画で現れた瞬間、取り込みフォームが高くなり、
  下のカレンダー全体が一気にズレる（カクッと跳ねる）。
- **設計**: サムネ置き場を**常設のラッパ `.intake-media` にして、中身が入ったら開く**。
  `grid-template-rows: 0fr → 1fr` ＋ `opacity` を `0.25s` でトランジション。
  高さが時間をかけて伸びるので、下の要素も滑らかに押し下がる。
  `prefers-reduced-motion: reduce` では無効化。
- **web/ 移植**（[CalendarPage.tsx](../web/src/pages/CalendarPage.tsx) の `IntakeForm`）:
  - サムネを `{preview && <div className="intake-thumbs">…}` で出し入れする現状を、
    **`.intake-media` を常に描画**し、その中に `preview` がある時だけ `.intake-thumb` を入れる形へ。
  - 開閉判定は `.intake-media:has(.intake-thumb)`（クラス制御不要）。
  - 子の `.intake-thumbs` に `overflow:hidden; min-height:0`（0fr 折りたたみのため）。

## ⑤ 普通の入力欄（AIを介さない手動追加＝小さなイベント作成フォーム）

- **症状/要望**: スクショ/テキスト＋AI抽出だけでなく、**手でイベントを足したい**。
  単発の予定ではなく、**同じイベント名でくくって予定を複数**入れられる形（実データモデル＝1イベント→N予定）を再現したい。
- **設計（改訂）**: 入力バー（`.intake`）の**枠の外・左にカレンダーicon `.intake-cal`** を置く
  （`.composer-row` で囲み、バー自体は中央のまま・icon は `position:absolute` で左外＝バー行に下端を合わせる）。
  押すと手動入力パネル `.manual-add` が**トグルで出てくる**（`aria-expanded` で開閉状態）。
  - パネルは**白背景・枠は付けない**（詳細画面と同じく素のまま）。中身は**イベント詳細画面とほぼ同じ**＝
    最上部に **`.title-form` のイベント名**（詳細と同じ部品）、その下に **`.sched` カードを複数**（`.sched-list`）。
    各予定は予定名／日付／終了／開始時刻／終了時刻／締切・目安に加え、**確定は `.sched-commit` 行の「確定」チェック1つ**
    （オンで `.sched.committed` 表示・浮いているが既定。**詳細画面の確定はトグルのまま**）。削除も `.sched-commit` 行（詳細と同じ削除ボタン）。
  - **幅は入力バーに合わせない**（`max-width` 無し＝詳細画面と同じ）が、コンポーザー（`.intake`）と
    手動フォーム（`.manual-add`）は**どちらも `margin-inline:auto` で中心をそろえる**（幅は違ってよい）。
  - **`.sched-add`「＋予定を追加」**で予定行を増やす（同じイベント名でくくる）。⑤⑧とも**全幅で統一**（`width:100%`）。
  - 送信は**`.manual-add__foot` の下センターの「追加」（`.primary`）**＝このイベントを作成。
  - **日付を空にした予定 → 日時未定**（①②③で固めた方針と同じ＝未定サイドバーに出る）。
- **バックエンド（要追加）**:
  - 新エンドポイント `POST /api/manual`（JSON: `event_title`, `schedules: [{title, date?, end_date?, time?, end_time?, is_deadline?, is_approximate?}]`, `month?`）。
  - 抽出器を**通さず**、`ExtractionInput(kind="manual", text=event_title)` と
    `ExtractionResult(event_title, schedules=[ExtractedSchedule(...) for ...])`
    を直接組んで `repository.create_event` に渡す。返りは取り込みと同じ `{month}`。
  - `ExtractionInput.kind` に `"manual"` を許可（現状 `"text"|"image"` 前提のコメントを更新）。
- **web/ 移植**: `IntakeForm` の `.intake-row` 先頭に `.intake-cal` ボタン＋ `useState` で `.manual-add` 開閉。
  予定行は `useState<予定[]>` で増減（送信まではクライアント保持）。
  パネル中身は `EventPage` の `ScheduleItem`/`sched-form` を抽出して共有コンポーネント化すると DRY（⑧と共用）。
  `api.ts` に `manualAdd()`、成功後は取り込みと同じ `onIntakeDone(landed)` で即時反映。

## ⑧ 詳細画面に予定を追加（既存イベントへグルーピング）

- **症状/要望**: 普通のチップから開いた**イベント詳細画面でも、同じイベントに予定を足したい**。
  現状の `EventPage` は予定の追加手段が無い。
- **設計**: `.sched-list` の下に **`.sched-add`「＋予定を追加」**（⑤と同じ部品）。
  押すと**空の予定を1件作成 → その場でインライン編集（自動保存）**。EventPage の既存の自動保存フローに乗る。
- **バックエンド（要追加）**: `POST /api/events/{id}/schedules`
  （空 or 最小フィールドで `schedules` に1件 INSERT、作成した予定 or 204 を返す）。
- **web/ 移植**: `EventPage` の `sched-list` 直後に `.sched-add`、`api.addSchedule(eventId)` 後に `load()`。

## ⑥ カレンダーが5週/6週でフッターが動く → 6週ぶん確保

- **症状**: 月により週数が 4〜6（`calendar.monthdatescalendar`）。行数でカレンダー高が変わり、
  下のフッターが上下する。
- **設計**: 表を `.cal-grid-wrap` で包み、**常に6週ぶんの高さを確保**
  （`min-block-size: calc(var(--cal-weekday-h) + 6 * var(--cal-day-h))`）。
  5週月は下に**余白**が残るだけで、フッター位置は固定。
  日セル高を `--cal-day-h` トークン化し、確保量と1か所で同期（モバイルは 84px）。
- **web/ 移植**: `<table class="cal-grid">` を `<div className="cal-grid-wrap">` で包むだけ。
- **代替案**（採れば CSS 不要・グリッドが常に埋まる）: バックエンドで**常に6週**返す
  （`build_month` で前後の月日をパディング）。余白を嫌うならこちら。今回は「余白でよい」前提で CSS 案を主とする。

## ⑦ 日時未定を右サイドバーへ（主張は弱め・常時表示）

- **症状/要望**: 未定リストがカレンダーの**下**にあって目立たない／雑然。
  右サイドバーに出したい。当初は折りたたみ（`.side-rail`）案だったが**廃止** →
  代わりに**常時出しつつ文字を小さく・色を抑えて主張を弱める**。
- **設計（改訂）**:
  - カレンダー画面を2カラム化 `.cal-layout`（左=カレンダー `minmax(0,1fr)` / 右=`.side-panel` 280px）。
  - **`.side-panel` 自体はカードにしない**（素の列）。代わりに**各未定を白背景チップ `.undated-card`**にし、
    **要確認（②）だけ黄色背景**。
  - パネル頭は小さなラベル「日時未定」＋件数（バッジでなく素の小文字）。**折りたたみ・side-rail は無し**。
  - 各未定は**白チップ `.undated-card`**：予定名 13px / イベント名・原文 11px で控えめ。
    `.undated`（旧・下部リスト）を置換。
  - **未定0件ならパネルごと隠す**。狭い画面（`max-width:880px`）では1カラムに積み、パネルはカレンダー下へ。
- **web/ 移植**: `CalendarPage` を `cal-layout` で囲み、`undated` を `aside.side-panel` に移設。
  折りたたみ state は不要（常時表示）。0件時は `undated.length > 0` でパネルごと出し分け。

## ②-UI 実在しない/読めない日付の「要確認」表示

- **症状**: 「6/31」など不正な日付は**未定に落とす**方針（コード対応済み）。だが未定に黙って入ると
  ユーザーが気づけない → **直すよう促す表示**が要る。
- **設計**: 未定カードに**要確認バリアント `.undated-card.needs-fix`**。
  amber の枠/地＋「日付を確認」バッジ＋原文（例「6/31」）を warning 色で表示。
  「7月中」「後日発表」のような**正当な未定はニュートラル**のまま（要確認にしない）。
- **バックエンド（要シグナル）**: データだけでは「読めない日付」と「そもそも日付が無い」を区別できない。
  - 案: API（`undated_schedules`）で **`needs_fix` を導出**。
    `date is None` かつ `raw_date_text` が**日付らしい表記（例 `M/D`・`M月D日`）にマッチするのに置けない**もの＝要確認。
    「7月中／後日発表」は M/D に完全一致しないのでニュートラル。
  - 型: `UndatedSchedule` に `needs_fix: bool` を追加し、フロント `types.ts` の `UndatedSchedule` にも反映。

---

## まとめ：移植チェックリスト

**web/（CSSは product-design から移植）**
- [ ] ① `.intake-media` 常設化＋ `:has` で開閉トランジション
- [ ] ⑤ `.intake-cal`（バー左icon）→ `.manual-add`（**詳細画面とほぼ同じ**: `.title-form`＋`.sched`複数・確定は `.commit-choice` ラジオ・`.sched-add`・下センター追加・幅は詳細準拠）をトグル＋ `api.manualAdd()`
- [ ] ⑥ `.cal-grid-wrap` で6週ぶん高さ確保（`--cal-day-h` トークン）
- [ ] ⑦ `cal-layout` 2カラム＋ `side-panel`（常時表示・控えめ）＋ `undated-card`（0件で非表示）
- [ ] ② `undated-card.needs-fix`（要確認）表示
- [ ] ⑧ `EventPage` の `sched-list` 下に `.sched-add`（既存イベントへ予定追加）＋ `api.addSchedule()`
- [ ] ⑤⑧ 予定エディタ（`sched-form`）を共有コンポーネント化して流用

**バックエンド（app/）**
- [ ] ⑤ `POST /api/manual`（`event_title`＋`schedules[]` を抽出を通さず create_event）／`ExtractionInput.kind="manual"` 許可
- [ ] ⑧ `POST /api/events/{id}/schedules`（既存イベントに予定1件 INSERT）
- [ ] ② `undated_schedules` に `needs_fix` 導出＋ `UndatedSchedule.needs_fix`／`types.ts` 反映
- [ ] ⑥（代替を採る場合のみ）`build_month` を常に6週返す
