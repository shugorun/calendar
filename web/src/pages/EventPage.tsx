import { useCallback, useEffect, useRef, useState } from 'react'
import type { ChangeEvent, FocusEvent, FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import * as api from '../api'
import type { EditableSchedule, EventDetail } from '../types'

function field(form: FormData, name: string): string {
  return String(form.get(name) ?? '')
}

// 4桁の数字を入力 → 24時間表記 hh:mm に自動整形（"1400" → "14:00"）。
function formatTime(event: ChangeEvent<HTMLInputElement>) {
  const digits = event.currentTarget.value.replace(/\D/g, '').slice(0, 4)
  event.currentTarget.value =
    digits.length > 2 ? `${digits.slice(0, 2)}:${digits.slice(2)}` : digits
}

function ScheduleItem({
  schedule,
  onChanged,
}: {
  schedule: EditableSchedule
  onChanged: () => void
}) {
  const formRef = useRef<HTMLFormElement>(null)
  const committed = schedule.commit_state === 'committed'

  // 自動保存: いずれかの項目が変わったらフォーム全体を送る（kind は UI 非編集なので現値を維持）。
  async function save() {
    const form = formRef.current
    if (!form) return
    const f = new FormData(form)
    await api.editSchedule(schedule.id, {
      title: field(f, 'title'),
      kind: schedule.kind,
      is_deadline: f.get('is_deadline') === 'on',
      is_approximate: f.get('is_approximate') === 'on',
      date: field(f, 'date') || null,
      end_date: field(f, 'end_date') || null,
      time: field(f, 'time') || null,
      end_time: field(f, 'end_time') || null,
    })
    onChanged()
  }

  async function remove() {
    await api.deleteSchedule(schedule.id)
    onChanged()
  }

  async function toggleCommit() {
    await api.commitSchedule(schedule.id, committed ? 'floating' : 'committed')
    onChanged()
  }

  return (
    <li className={`sched ${schedule.commit_state}`}>
      <form
        ref={formRef}
        className="sched-form"
        aria-label={`予定「${schedule.title}」の編集`}
        onSubmit={(e) => e.preventDefault()}
      >
        <input
          className="sched-title"
          name="title"
          defaultValue={schedule.title}
          aria-label="予定名"
          onBlur={save}
        />
        <label>
          日付{' '}
          <input
            type="date"
            name="date"
            defaultValue={schedule.date ?? ''}
            onChange={save}
          />
        </label>
        <label>
          終了{' '}
          <input
            type="date"
            name="end_date"
            defaultValue={schedule.end_date ?? ''}
            onChange={save}
          />
        </label>
        <label>
          開始時刻{' '}
          <input
            type="text"
            name="time"
            defaultValue={schedule.time ? schedule.time.slice(0, 5) : ''}
            placeholder="hh:mm"
            maxLength={5}
            inputMode="numeric"
            onChange={formatTime}
            onBlur={save}
          />
        </label>
        <label>
          終了時刻{' '}
          <input
            type="text"
            name="end_time"
            defaultValue={
              schedule.end_time ? schedule.end_time.slice(0, 5) : ''
            }
            placeholder="hh:mm"
            maxLength={5}
            inputMode="numeric"
            onChange={formatTime}
            onBlur={save}
          />
        </label>
        <span className="sched-flags">
          <label className="check">
            <input
              type="checkbox"
              name="is_deadline"
              defaultChecked={schedule.is_deadline}
              onChange={save}
            />{' '}
            締切
          </label>
          <label className="check">
            <input
              type="checkbox"
              name="is_approximate"
              defaultChecked={schedule.is_approximate}
              onChange={save}
            />{' '}
            目安
          </label>
          {schedule.raw_date_text && (
            <span className="raw">原文: {schedule.raw_date_text}</span>
          )}
        </span>
      </form>
      <div className="sched-commit">
        <span className="sched-state">{committed ? '確定' : '浮いている'}</span>
        <button
          type="button"
          className={committed ? undefined : 'primary'}
          onClick={toggleCommit}
          aria-label={
            committed
              ? `「${schedule.title}」の確定を取り消す`
              : `「${schedule.title}」を確定にする`
          }
        >
          {committed ? '確定を取り消す' : '確定にする'}
        </button>
        <button type="button" className="danger" onClick={remove}>
          削除
        </button>
      </div>
    </li>
  )
}

export function EventPage() {
  const { id } = useParams()
  const eventId = Number(id)
  const navigate = useNavigate()
  const [event, setEvent] = useState<EventDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    api
      .getEvent(eventId)
      .then(setEvent)
      .catch((e: unknown) => setError(String(e)))
  }, [eventId])

  useEffect(() => {
    load()
  }, [load])

  if (error) return <p role="alert">読み込みに失敗しました: {error}</p>
  if (!event) return <p role="status">読み込み中…</p>

  const total = event.schedules.length
  const allCommitted = total > 0 && event.committed_count === total
  const home = event.home_month ? `/?month=${event.home_month}` : '/'

  async function saveTitle(e: FocusEvent<HTMLInputElement>) {
    await api.editEventTitle(eventId, e.currentTarget.value)
    load()
  }

  async function toggleAll() {
    await api.commitEvent(eventId, allCommitted ? 'floating' : 'committed')
    load()
  }

  async function saveNote(e: FocusEvent<HTMLTextAreaElement>) {
    await api.editNote(eventId, e.currentTarget.value)
    load()
  }

  async function removeEvent(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    await api.deleteEvent(eventId)
    navigate('/')
  }

  return (
    <>
      <nav aria-label="ページ移動">
        <Link className="back-link" to={home}>
          ← カレンダーへ戻る
        </Link>
      </nav>

      <header className="event-head">
        <h1 className="event-title">{event.title}</h1>
        {total > 0 && (
          <button
            type="button"
            className={allCommitted ? undefined : 'primary'}
            onClick={toggleAll}
          >
            {allCommitted ? '予定の確定を取り消す' : '予定をまとめて確定'}
          </button>
        )}
      </header>

      <form
        className="title-form"
        aria-label="イベント名の変更"
        onSubmit={(e) => e.preventDefault()}
      >
        <label htmlFor="event-title">イベント名</label>
        <input
          id="event-title"
          name="title"
          defaultValue={event.title}
          onBlur={saveTitle}
        />
      </form>

      {total === 0 ? (
        <p className="empty">予定はありません（日付を入れると追えます）。</p>
      ) : (
        <ul className="sched-list">
          {event.schedules.map((s) => (
            <ScheduleItem key={s.id} schedule={s} onChanged={load} />
          ))}
        </ul>
      )}

      <form
        className="note-form"
        aria-label="ノート"
        onSubmit={(e) => e.preventDefault()}
      >
        <textarea
          id="event-note"
          name="note"
          rows={4}
          defaultValue={event.note}
          placeholder="補足メモを書く"
          aria-label="ノート"
          onBlur={saveNote}
        />
      </form>

      {event.has_image && (
        <img
          className="source-image"
          src={`/api/events/${event.id}/image`}
          alt="取り込んだ画像"
        />
      )}
      {event.source_text && <pre className="source">{event.source_text}</pre>}
      {!event.has_image && !event.source_text && (
        <p className="empty">元入力はありません。</p>
      )}

      <form className="delete-event" onSubmit={removeEvent}>
        <button type="submit" className="danger">
          このイベントを削除
        </button>
      </form>
    </>
  )
}
