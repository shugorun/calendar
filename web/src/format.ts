// ISO 日付（"YYYY-MM-DD"）を、読み上げ向けの日本語日付に整える。
export function isoToJaDate(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${Number(y)}年${Number(m)}月${Number(d)}日`
}

// 数字入力を 24 時間表記 hh:mm に整形（"1400" → "14:00"）。制御入力用の純関数。
export function formatTimeInput(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 4)
  return digits.length > 2 ? `${digits.slice(0, 2)}:${digits.slice(2)}` : digits
}

// 数字入力を YYYY-MM-DD に整形（"20260620" → "2026-06-20"）。打鍵に応じて段階的に。
export function formatDateInput(value: string): string {
  const d = value.replace(/\D/g, '').slice(0, 8)
  if (d.length <= 4) return d
  if (d.length <= 6) return `${d.slice(0, 4)}-${d.slice(4)}`
  return `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6)}`
}

// 完全で実在する YYYY-MM-DD だけを返す。未完成・不正（例 2026-06-31）は null。
export function toIsoDateOrNull(value: string): string | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!m) return null
  const [y, mo, d] = [Number(m[1]), Number(m[2]), Number(m[3])]
  const dt = new Date(y, mo - 1, d)
  const real =
    dt.getFullYear() === y && dt.getMonth() === mo - 1 && dt.getDate() === d
  return real ? value : null
}
