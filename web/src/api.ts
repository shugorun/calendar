import type {
  CalendarResponse,
  CommitState,
  EventDetail,
  ManualEventInput,
  ScheduleEdit,
} from './types'

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    throw new Error(`${init?.method ?? 'GET'} ${url} failed: ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

function postJson<T>(url: string, body: unknown): Promise<T> {
  return request<T>(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function getCalendar(month: string | null): Promise<CalendarResponse> {
  const query = month ? `?month=${encodeURIComponent(month)}` : ''
  return request<CalendarResponse>(`/api/calendar${query}`)
}

export function intake(form: FormData): Promise<{ month: string }> {
  return request<{ month: string }>('/api/intake', {
    method: 'POST',
    body: form,
  })
}

export function manualAdd(body: ManualEventInput): Promise<{ month: string }> {
  return postJson<{ month: string }>('/api/manual', body)
}

export function addSchedule(eventId: number): Promise<{ id: number }> {
  return postJson<{ id: number }>(`/api/events/${eventId}/schedules`, {})
}

export function getEvent(id: number): Promise<EventDetail> {
  return request<EventDetail>(`/api/events/${id}`)
}

export function editEventTitle(id: number, title: string): Promise<void> {
  return postJson<void>(`/api/events/${id}/edit`, { title })
}

export function commitEvent(id: number, state: CommitState): Promise<void> {
  return postJson<void>(`/api/events/${id}/commit`, { state })
}

export function editNote(id: number, note: string): Promise<void> {
  return postJson<void>(`/api/events/${id}/note`, { note })
}

export function deleteEvent(id: number): Promise<void> {
  return postJson<void>(`/api/events/${id}/delete`, {})
}

export function commitSchedule(id: number, state: CommitState): Promise<void> {
  return postJson<void>(`/api/schedules/${id}/commit`, { state })
}

export function editSchedule(id: number, body: ScheduleEdit): Promise<void> {
  return postJson<void>(`/api/schedules/${id}/edit`, body)
}

export function deleteSchedule(id: number): Promise<void> {
  return postJson<void>(`/api/schedules/${id}/delete`, {})
}
