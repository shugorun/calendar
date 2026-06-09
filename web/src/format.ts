// ISO 日付（"YYYY-MM-DD"）を、読み上げ向けの日本語日付に整える。
export function isoToJaDate(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${Number(y)}年${Number(m)}月${Number(d)}日`
}
