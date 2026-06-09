import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { formatDateInput, formatTimeInput, toIsoDateOrNull } from '../format'
import type { ManualScheduleInput } from '../types'
import { IntakeComposer } from './IntakeComposer'

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

function toInput(s: ManualSched): ManualScheduleInput {
  return {
    title: s.title,
    date: toIsoDateOrNull(s.date), // 未完成・不正な日付は日時未定にする
    end_date: toIsoDateOrNull(s.end_date),
    time: s.time || null,
    end_time: s.end_time || null,
    is_deadline: s.is_deadline,
    is_approximate: s.is_approximate,
    committed: s.committed,
  }
}

// 手動入力フォーム。withEventTitle でイベント名欄の有無を切替（カレンダー＝新規
// イベント作成なので有り、イベント詳細＝既存に追加なので無し）。
function ManualForm({
  withEventTitle,
  onSubmit,
}: {
  withEventTitle: boolean
  onSubmit: (
    eventTitle: string,
    schedules: ManualScheduleInput[],
  ) => Promise<void>
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

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    try {
      await onSubmit(eventTitle, scheds.map(toInput))
    } finally {
      setSubmitting(false)
    }
  }

  // 予定に中身があれば保存できる（カレンダーはイベント名だけでも可＝名前は補完される）。
  const hasContent =
    (withEventTitle && eventTitle.trim().length > 0) ||
    scheds.some((s) => s.title.trim().length > 0 || s.date.length > 0)
  const canSubmit = hasContent && !submitting

  return (
    <form
      className="manual-add"
      aria-label={withEventTitle ? 'イベントを手で追加' : '予定を手で追加'}
      onSubmit={submit}
    >
      {withEventTitle && (
        <div className="title-form">
          <label htmlFor="manual-event">イベント名</label>
          <input
            id="manual-event"
            value={eventTitle}
            onChange={(e) => setEventTitle(e.target.value)}
            placeholder="イベントを入力してください"
          />
        </div>
      )}
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
                placeholder="予定を入力してください"
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

// 取り込みバー（左にカレンダーicon）＋トグルで開く手動入力フォーム。
// カレンダー（新規イベント作成）とイベント詳細（既存へ追加）で使い回す。
export function Composer({
  intakeSubmit,
  manualWithEventTitle,
  manualSubmit,
}: {
  intakeSubmit: (form: FormData) => Promise<void>
  manualWithEventTitle: boolean
  manualSubmit: (
    eventTitle: string,
    schedules: ManualScheduleInput[],
  ) => Promise<void>
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
        <IntakeComposer submit={intakeSubmit} />
      </div>
      {/* 常設して 0fr→1fr で「ぬるっと」開く。閉じている間は inert で操作不可に */}
      <div
        className={manualOpen ? 'manual-reveal is-open' : 'manual-reveal'}
        inert={!manualOpen}
      >
        <ManualForm
          key={formKey}
          withEventTitle={manualWithEventTitle}
          onSubmit={async (eventTitle, schedules) => {
            await manualSubmit(eventTitle, schedules)
            setManualOpen(false)
            setFormKey((k) => k + 1)
          }}
        />
      </div>
    </div>
  )
}
