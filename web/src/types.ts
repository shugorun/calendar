// バックエンド（FastAPI）が返す JSON の形。app/repository.py の dataclass に対応する。

export type CommitState = 'floating' | 'committed'

export interface DatedSchedule {
  event_id: number
  event_title: string
  commit_state: CommitState
  title: string
  is_deadline: boolean
  is_approximate: boolean
  date: string // "YYYY-MM-DD"
  end_date: string | null
  time: string | null // "HH:MM:SS"（表示時は先頭5文字）
}

export interface UndatedSchedule {
  event_id: number
  event_title: string
  title: string
  raw_date_text: string | null
}

export interface DayCell {
  day: string // "YYYY-MM-DD"
  in_month: boolean
  schedules: DatedSchedule[]
}

export interface MonthView {
  year: number
  month: number
  ym: string // "YYYY-MM"
  weeks: DayCell[][]
  prev_month: string
  next_month: string
}

export interface CalendarResponse {
  view: MonthView
  undated: UndatedSchedule[]
  weekday_labels: string[]
  today: string // "YYYY-MM-DD"
}

export interface EditableSchedule {
  id: number
  title: string
  kind: string | null
  is_deadline: boolean
  is_approximate: boolean
  date: string | null
  end_date: string | null
  time: string | null
  end_time: string | null
  raw_date_text: string | null
  commit_state: CommitState
}

export interface EventDetail {
  id: number
  title: string
  source_kind: string
  note: string
  has_image: boolean
  source_text: string | null
  schedules: EditableSchedule[]
  committed_count: number
  home_month: string | null
}

export interface ScheduleEdit {
  title: string
  kind: string | null
  is_deadline: boolean
  is_approximate: boolean
  date: string | null
  end_date: string | null
  time: string | null
  end_time: string | null
}
