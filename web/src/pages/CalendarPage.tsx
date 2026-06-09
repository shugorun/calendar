import { useCallback, useEffect, useRef, useState } from 'react'
import type { ChangeEvent, CSSProperties, FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getCalendar, intake } from '../api'
import { isoToJaDate } from '../format'
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
          {s.title}
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
          placeholder="予定を貼り付け、または画像を追加…"
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

  if (error) return <p role="alert">読み込みに失敗しました: {error}</p>
  if (!data) return <p role="status">読み込み中…</p>

  const { view, undated, weekday_labels, today } = data

  return (
    <>
      <h1>Floaty</h1>

      <IntakeForm month={view.ym} onDone={goMonth} />

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
      </section>

      {undated.length > 0 && (
        <section className="undated" aria-label="日時未定の予定">
          <h2>日時未定</h2>
          <ul>
            {undated.map((s) => (
              <li key={`${s.event_id}-${s.title}`}>
                <Link className="what" to={`/events/${s.event_id}`}>
                  {s.title}
                </Link>{' '}
                <span className="ev">{s.event_title}</span>
                {s.raw_date_text && (
                  <span className="raw">（{s.raw_date_text}）</span>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  )
}
