import { useCallback, useEffect, useRef, useState } from 'react'
import type { ChangeEvent, CSSProperties, FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getCalendar, intake, manualAdd } from '../api'
import {
  formatDateInput,
  formatTimeInput,
  isoToJaDate,
  toIsoDateOrNull,
} from '../format'
import type { CalendarResponse, DatedSchedule, DayCell } from '../types'

const MAX_CHIPS = 3

const WEEKDAY_FULL: Record<string, string> = {
  日: '日曜日',
  月: '月曜日',
  火: '火曜日',
  水: '水曜日',
  木: '木曜日',
  金: '金曜日',
  土: '土曜日',
}

function dayNumber(iso: string): number {
  return Number(iso.slice(8, 10))
}

// イベント名があれば「イベント名 予定名」と前置きして表示する（予定名は短く、
// イベント名を繰り返さない前提＝抽出プロンプトでそのように指示している）。
function displayName(eventTitle: string, title: string): string {
  return eventTitle ? `${eventTitle} ${title}` : title
}

// チップは記号に頼らず、読み上げで文脈が分かる accessible name を組み立てる。
function chipLabel(s: DatedSchedule): string {
  const parts = [isoToJaDate(s.date)]
  if (s.time) parts.push(s.time.slice(0, 5))
  parts.push(`${s.event_title}：${s.title}`)
  if (s.is_deadline) parts.push('締切')
  if (s.is_approximate) parts.push('（日付は目安）')
  return parts.join(' ')
}

function ScheduleChip({ s }: { s: DatedSchedule }) {
  const time = s.time ? s.time.slice(0, 5) : null
  const classes = ['chip', s.commit_state]
  if (s.is_deadline) classes.push('deadline')
  if (s.is_approximate) classes.push('approximate')
  return (
    <li className={classes.join(' ')}>
      <Link to={`/events/${s.event_id}`} aria-label={chipLabel(s)}>
        {time && <span className="chip-time">{time} </span>}
        <span className="chip-name">
          {s.is_deadline && <span aria-hidden="true">⚑</span>}
          {displayName(s.event_title, s.title)}
          {s.is_approximate && <span aria-hidden="true"> ~</span>}
        </span>
      </Link>
    </li>
  )
}

// 1日のセル。予定が MAX_CHIPS を超えたら先頭だけ並べ、残りはポップオーバーに集約。
function CalDay({ cell, today }: { cell: DayCell; today: string }) {
  const isToday = cell.day === today
  const classes = ['cal-day']
  if (!cell.in_month) classes.push('out')
  if (isToday) classes.push('today')

  const total = cell.schedules.length
  const overflow = total > MAX_CHIPS
  const shown = overflow ? cell.schedules.slice(0, MAX_CHIPS) : cell.schedules
  const popId = `day-pop-${cell.day}`
  const anchor = `--day-${cell.day.replace(/-/g, '')}`

  return (
    <td className={classes.join(' ')}>
      <time
        className="cal-daynum"
        dateTime={cell.day}
        aria-label={isoToJaDate(cell.day)}
        aria-current={isToday ? 'date' : undefined}
      >
        {dayNumber(cell.day)}
      </time>
      {total > 0 && (
        <ul className="cal-chips">
          {shown.map((s, i) => (
            <ScheduleChip key={`${s.event_id}-${s.title}-${i}`} s={s} />
          ))}
          {overflow && (
            <li className="cal-more">
              <button
                type="button"
                popoverTarget={popId}
                style={{ anchorName: anchor } as CSSProperties}
              >
                ＋{total - MAX_CHIPS}件
              </button>
            </li>
          )}
        </ul>
      )}
      {overflow && (
        <div
          className="day-popover"
          id={popId}
          popover="auto"
          style={{ positionAnchor: anchor } as CSSProperties}
        >
          <div className="day-popover__head">
            <span className="day-popover__date">{isoToJaDate(cell.day)}</span>
            <button
              type="button"
              className="day-popover__x"
              popoverTarget={popId}
              popoverTargetAction="hide"
              aria-label="閉じる"
            >
              ×
            </button>
          </div>
          <ul className="cal-chips">
            {cell.schedules.map((s, i) => (
              <ScheduleChip key={`${s.event_id}-${s.title}-${i}`} s={s} />
            ))}
          </ul>
        </div>
      )}
    </td>
  )
}

function IntakeForm({
  month,
  onDone,
}: {
  month: string
  onDone: (landedMonth: string) => void
}) {
  const [preview, setPreview] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const formRef = useRef<HTMLFormElement>(null)

  const showFile = useCallback((file: File) => {
    setPreview(URL.createObjectURL(file))
  }, [])

  // スクショをページ上で Ctrl+V → file input にセットして一緒に送信できるようにする。
  useEffect(() => {
    function onPaste(event: ClipboardEvent) {
      const items = event.clipboardData?.items
      if (!items || !fileRef.current) return
      for (const item of Array.from(items)) {
        if (!item.type.startsWith('image/')) continue
        const file = item.getAsFile()
        if (!file) continue
        const transfer = new DataTransfer()
        transfer.items.add(file)
        fileRef.current.files = transfer.files
        showFile(file)
        event.preventDefault()
        break
      }
    }
    window.addEventListener('paste', onPaste)
    return () => window.removeEventListener('paste', onPaste)
  }, [showFile])

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (file) showFile(file)
  }

  function clearImage() {
    if (fileRef.current) fileRef.current.value = ''
    setPreview(null)
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    const form = new FormData(event.currentTarget)
    form.set('month', month)
    try {
      const { month: landed } = await intake(form)
      formRef.current?.reset()
      setPreview(null)
      onDone(landed)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form
      ref={formRef}
      className="intake"
      onSubmit={onSubmit}
      aria-label="予定の取り込み"
      aria-busy={submitting}
    >
      {/* サムネ置き場は常設し、画像が入ったら CSS で滑らかに開く（:has） */}
      <div className="intake-media">
        {preview && (
          <div className="intake-thumbs">
            <div className="intake-thumb">
              <img
                className="preview"
                src={preview}
                alt="取り込む画像のプレビュー"
              />
              <button
                type="button"
                className="intake-thumb-x"
                aria-label="この画像を外す"
                onClick={clearImage}
              >
                ×
              </button>
            </div>
          </div>
        )}
      </div>
      <div className="intake-row">
        <label className="intake-add" aria-label="画像を追加">
          +
          <input
            ref={fileRef}
            type="file"
            name="image"
            accept="image/*"
            hidden
            onChange={onFileChange}
          />
        </label>
        <textarea
          name="text"
          aria-label="取り込むテキスト"
          placeholder="予定が書かれた画像やテキストを貼り付けてください。"
        />
        <button
          type="submit"
          className="intake-submit"
          disabled={submitting}
          aria-label="取り込む"
        >
          ↑
        </button>
      </div>
    </form>
  )
}

interface ManualSched {
  id: number
  title: string
  date: string
  end_date: string
  time: string
  end_time: string
  is_deadline: boolean
  is_approximate: boolean
  committed: boolean
}

function blankSched(id: number): ManualSched {
  return {
    id,
    title: '',
    date: '',
    end_date: '',
    time: '',
    end_time: '',
    is_deadline: false,
    is_approximate: false,
    committed: false,
  }
}

// 手動追加: AIを介さず「イベント名＋予定を複数」で1イベントを作る（詳細画面とほぼ同じ）。
function ManualForm({
  month,
  onDone,
}: {
  month: string
  onDone: (landedMonth: string) => void
}) {
  const [eventTitle, setEventTitle] = useState('')
  const [scheds, setScheds] = useState<ManualSched[]>(() => [blankSched(0)])
  const [submitting, setSubmitting] = useState(false)
  const nextId = useRef(1)

  function update(id: number, patch: Partial<ManualSched>) {
    setScheds((prev) => prev.map((s) => (s.id === id ? { ...s, ...patch } : s)))
  }
  function addSched() {
    setScheds((prev) => [...prev, blankSched(nextId.current++)])
  }
  function removeSched(id: number) {
    setScheds((prev) =>
      prev.length > 1 ? prev.filter((s) => s.id !== id) : prev,
    )
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    try {
      const { month: landed } = await manualAdd({
        event_title: eventTitle,
        month,
        schedules: scheds.map((s) => ({
          title: s.title,
          date: toIsoDateOrNull(s.date), // 未完成・不正な日付は日時未定にする
          end_date: toIsoDateOrNull(s.end_date),
          time: s.time || null,
          end_time: s.end_time || null,
          is_deadline: s.is_deadline,
          is_approximate: s.is_approximate,
          committed: s.committed,
        })),
      })
      onDone(landed)
    } finally {
      setSubmitting(false)
    }
  }

  // イベント名が空でも、予定に中身があれば保存できる（バックは名前を「取り込み」に補完）。
  const hasContent =
    eventTitle.trim().length > 0 ||
    scheds.some((s) => s.title.trim().length > 0 || s.date.length > 0)
  const canSubmit = hasContent && !submitting

  return (
    <form
      className="manual-add"
      aria-label="イベントを手で追加"
      onSubmit={onSubmit}
    >
      <div className="title-form">
        <label htmlFor="manual-event">イベント名</label>
        <input
          id="manual-event"
          value={eventTitle}
          onChange={(e) => setEventTitle(e.target.value)}
          placeholder="イベントの名前を入力してください"
        />
      </div>
      <ul className="sched-list">
        {scheds.map((s, i) => (
          <li
            key={s.id}
            className={`sched ${s.committed ? 'committed' : 'floating'}`}
          >
            <div
              className="sched-form"
              role="group"
              aria-label={`予定${i + 1}`}
            >
              <input
                className="sched-title"
                value={s.title}
                aria-label="予定名"
                placeholder="予定の名前を入力してください"
                onChange={(e) => update(s.id, { title: e.target.value })}
              />
              <label>
                日付{' '}
                <input
                  type="text"
                  className="sched-date"
                  value={s.date}
                  placeholder="yyyy-mm-dd"
                  maxLength={10}
                  inputMode="numeric"
                  onChange={(e) =>
                    update(s.id, { date: formatDateInput(e.target.value) })
                  }
                />
              </label>
              <label>
                終了{' '}
                <input
                  type="text"
                  className="sched-date"
                  value={s.end_date}
                  placeholder="yyyy-mm-dd"
                  maxLength={10}
                  inputMode="numeric"
                  onChange={(e) =>
                    update(s.id, { end_date: formatDateInput(e.target.value) })
                  }
                />
              </label>
              <label>
                開始時刻{' '}
                <input
                  type="text"
                  value={s.time}
                  placeholder="hh:mm"
                  maxLength={5}
                  inputMode="numeric"
                  onChange={(e) =>
                    update(s.id, { time: formatTimeInput(e.target.value) })
                  }
                />
              </label>
              <label>
                終了時刻{' '}
                <input
                  type="text"
                  value={s.end_time}
                  placeholder="hh:mm"
                  maxLength={5}
                  inputMode="numeric"
                  onChange={(e) =>
                    update(s.id, { end_time: formatTimeInput(e.target.value) })
                  }
                />
              </label>
              <span className="sched-flags">
                <label className="check">
                  <input
                    type="checkbox"
                    checked={s.is_deadline}
                    onChange={(e) =>
                      update(s.id, { is_deadline: e.target.checked })
                    }
                  />{' '}
                  締切
                </label>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={s.is_approximate}
                    onChange={(e) =>
                      update(s.id, { is_approximate: e.target.checked })
                    }
                  />{' '}
                  目安
                </label>
              </span>
            </div>
            <div className="sched-commit">
              <label className="check commit-check">
                <input
                  type="checkbox"
                  checked={s.committed}
                  onChange={(e) =>
                    update(s.id, { committed: e.target.checked })
                  }
                />{' '}
                確定
              </label>
              <button
                type="button"
                className="danger"
                onClick={() => removeSched(s.id)}
                disabled={scheds.length === 1}
              >
                削除
              </button>
            </div>
          </li>
        ))}
      </ul>
      <button type="button" className="sched-add" onClick={addSched}>
        ＋予定を追加
      </button>
      <div className="manual-add__foot">
        <button type="submit" className="primary" disabled={!canSubmit}>
          追加
        </button>
      </div>
    </form>
  )
}

// 取り込みバー（左にカレンダーicon）と、トグルで開く手動追加フォーム。
function Composer({
  month,
  onDone,
}: {
  month: string
  onDone: (landedMonth: string) => void
}) {
  const [manualOpen, setManualOpen] = useState(false)
  // 送信後はフォームを作り直す（key を変えて未開状態でリセット）。
  const [formKey, setFormKey] = useState(0)
  return (
    <div className="composer">
      <div className="composer-row">
        <button
          type="button"
          className="intake-cal"
          aria-label="手で追加"
          aria-expanded={manualOpen}
          onClick={() => setManualOpen((open) => !open)}
        >
          <svg
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          >
            <rect x="3.5" y="5" width="17" height="16" rx="2" />
            <line x1="3.5" y1="9.5" x2="20.5" y2="9.5" />
            <line x1="8" y1="3" x2="8" y2="6" />
            <line x1="16" y1="3" x2="16" y2="6" />
          </svg>
        </button>
        <IntakeForm month={month} onDone={onDone} />
      </div>
      {/* 常設して 0fr→1fr で「ぬるっと」開く。閉じている間は inert で操作不可に */}
      <div
        className={manualOpen ? 'manual-reveal is-open' : 'manual-reveal'}
        inert={!manualOpen}
      >
        <ManualForm
          key={formKey}
          month={month}
          onDone={(landed) => {
            setManualOpen(false)
            setFormKey((k) => k + 1)
            onDone(landed)
          }}
        />
      </div>
    </div>
  )
}

export function CalendarPage() {
  const [params, setParams] = useSearchParams()
  const month = params.get('month')
  const [data, setData] = useState<CalendarResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    getCalendar(month)
      .then(setData)
      .catch((e: unknown) => setError(String(e)))
  }, [month])

  useEffect(() => {
    load()
  }, [load])

  function goMonth(ym: string) {
    setParams(ym ? { month: ym } : {})
  }

  // 取り込み後は表示を必ず更新する。着地先が今見ている月と同じ（＝月が
  // 変わらず useEffect が再取得しない）ときや未定の予定でも漏れず出すため。
  function onIntakeDone(landed: string) {
    if (landed !== month) goMonth(landed)
    else load()
  }

  if (error) return <p role="alert">読み込みに失敗しました: {error}</p>
  if (!data) return <p role="status">読み込み中…</p>

  const { view, undated, weekday_labels, today } = data
  const hasUndated = undated.length > 0

  return (
    <>
      <h1>Floaty</h1>

      <Composer month={view.ym} onDone={onIntakeDone} />

      <div className={hasUndated ? 'cal-layout' : undefined}>
        <section className="calendar" aria-label="月カレンダー">
          <nav className="cal-nav" aria-label="月の移動">
            <button type="button" onClick={() => goMonth(view.prev_month)}>
              ‹ 前の月
            </button>
            <h2 aria-live="polite">
              {view.year}年{view.month}月
            </h2>
            <button type="button" onClick={() => goMonth(view.next_month)}>
              次の月 ›
            </button>
          </nav>

          <div className="cal-grid-wrap">
            <table className="cal-grid">
              <thead>
                <tr>
                  {weekday_labels.map((label) => (
                    <th
                      key={label}
                      scope="col"
                      className="cal-weekday"
                      aria-label={WEEKDAY_FULL[label] ?? label}
                    >
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {view.weeks.map((week) => (
                  <tr key={week[0].day}>
                    {week.map((cell) => (
                      <CalDay key={cell.day} cell={cell} today={today} />
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {hasUndated && (
          <aside className="side-panel" aria-label="日時未定の予定">
            <div className="side-panel__head">
              <span className="side-panel__title">日時未定</span>
              <span className="side-panel__count">{undated.length}</span>
            </div>
            <div className="undated-list">
              {undated.map((s) => (
                <Link
                  key={`${s.event_id}-${s.title}`}
                  className={
                    s.needs_fix ? 'undated-card needs-fix' : 'undated-card'
                  }
                  to={`/events/${s.event_id}`}
                >
                  <span className="undated-card__what">
                    {displayName(s.event_title, s.title)}
                  </span>
                  {s.raw_date_text && (
                    <span className="undated-card__raw">{s.raw_date_text}</span>
                  )}
                  {s.needs_fix && <span className="badge-fix">日付を確認</span>}
                </Link>
              ))}
            </div>
          </aside>
        )}
      </div>
    </>
  )
}
