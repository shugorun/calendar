import { useCallback, useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getCalendar, intake, manualAdd } from '../api'
import { Composer } from '../components/Composer'
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

  const { view, undated, eventless, weekday_labels, today } = data
  const hasSidePanel = undated.length > 0 || eventless.length > 0

  return (
    <>
      <h1>Floaty</h1>

      <Composer
        intakeSubmit={async (form) => {
          form.set('month', view.ym)
          const { month: landed } = await intake(form)
          onIntakeDone(landed)
        }}
        manualWithEventTitle
        manualSubmit={async (eventTitle, schedules) => {
          const { month: landed } = await manualAdd({
            event_title: eventTitle,
            schedules,
            month: view.ym,
          })
          onIntakeDone(landed)
        }}
      />

      <div className={hasSidePanel ? 'cal-layout' : undefined}>
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

        {hasSidePanel && (
          <aside className="side-panel" aria-label="日時未定・予定なし">
            <div className="side-panel__head">
              <span className="side-panel__title">日時未定</span>
              <span className="side-panel__count">
                {undated.length + eventless.length}
              </span>
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
              {eventless.map((e) => (
                <Link
                  key={`eventless-${e.event_id}`}
                  className="undated-card"
                  to={`/events/${e.event_id}`}
                >
                  <span className="undated-card__what">{e.event_title}</span>
                  <span className="undated-card__raw">予定なし</span>
                </Link>
              ))}
            </div>
          </aside>
        )}
      </div>
    </>
  )
}
