export const fmtDate = (iso: string, opts: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric', year: 'numeric' }) =>
  new Date(iso).toLocaleDateString('en-PH', { ...opts, timeZone: 'Asia/Manila' })
export const fmtTime = (iso: string) => new Date(iso).toLocaleTimeString('en-PH', { hour: 'numeric', minute: '2-digit', timeZone: 'Asia/Manila' })
export const fmtDateTime = (iso: string) => `${fmtDate(iso)}, ${fmtTime(iso)}`
export const fmtDay = (iso: string) => new Date(iso).toLocaleDateString('en-PH', { weekday: 'long', month: 'long', day: 'numeric', timeZone: 'Asia/Manila' })
export const peso = (n: number) => new Intl.NumberFormat('en-PH', { style: 'currency', currency: 'PHP' }).format(n)
const manilaDay = new Intl.DateTimeFormat('en-CA', { year: 'numeric', month: '2-digit', day: '2-digit', timeZone: 'Asia/Manila' })
export const dayKey = (iso: string) => manilaDay.format(new Date(iso))
export const relative = (iso: string) => {
  const diff = new Date(iso).getTime() - Date.now()
  const days = Math.round(diff / 86_400_000)
  const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })
  if (Math.abs(diff) < 3_600_000) return rtf.format(Math.round(diff / 60_000), 'minute')
  if (Math.abs(diff) < 86_400_000) return rtf.format(Math.round(diff / 3_600_000), 'hour')
  return rtf.format(days, 'day')
}
export const age = (dob: string | null) => {
  if (!dob) return null
  const d = new Date(dob)
  const n = new Date()
  let a = n.getFullYear() - d.getFullYear()
  if (n < new Date(n.getFullYear(), d.getMonth(), d.getDate())) a--
  return a
}
export const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, ' ')


export function clinicStatus(now = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Manila' }))) {
  const day = now.getDay()
  const h = now.getHours() + now.getMinutes() / 60
  const close = day === 6 ? 12 : day === 0 ? 0 : 17
  if (day !== 0 && h >= 8 && h < close) return { open: true, label: `Open now · closes ${close === 12 ? '12:00 PM' : '5:00 PM'}` }
  const opensTomorrow = h >= close || day === 0
  const nextDay = opensTomorrow ? (day === 6 ? 'Monday' : day === 0 ? 'Monday' : 'tomorrow') : 'today'
  return { open: false, label: `Closed · opens ${nextDay} at 8:00 AM` }
}
