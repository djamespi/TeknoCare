import { useMemo, useState } from 'react'
import { Check, Clock, MapPin, Stethoscope, Wallet, Sparkles } from 'lucide-react'
import { Button, Card, Empty, PageHeader, Textarea, cx } from '../../components/ui'
import { dayKey, fmtDay, fmtTime } from '../../data/format'
import { useLookups, useStore } from '../../data/store'
import { useNav } from '../../nav'
import { PendingPatientBanner } from '../../components/PendingPatientBanner'
import { bookingImage, careIcon } from './bookingPhotos'

export function BookVisit() {
  const { db, me, actions } = useStore()
  const { go, run, segments } = useNav()
  const { providerName, roomById, bookedSlots } = useLookups()
  const providers = db.provider.filter((p) => p.eligible && p.provider_type !== 'unverified')
  const pre = Number(segments[1])
  const [provider, setProvider] = useState(providers.some((p) => p.provider_id === pre) ? pre : providers[0]?.provider_id)
  const open = useMemo(
    () => db.slot.filter((s) => s.provider_id === provider && s.bookable && !bookedSlots.has(s.slot_id) && new Date(s.start_time) > new Date()).sort((a, b) => a.start_time.localeCompare(b.start_time)),
    [db.slot, provider, bookedSlots],
  )
  const days = useMemo(() => {
    const m = new Map<string, typeof open>()
    open.forEach((s) => m.set(dayKey(s.start_time), [...(m.get(dayKey(s.start_time)) ?? []), s]))
    return [...m.entries()].slice(0, 12)
  }, [open])
  const [day, setDay] = useState<string | null>(null)
  const activeDay = day && days.some(([k]) => k === day) ? day : days[0]?.[0]
  const [slotId, setSlotId] = useState<number | null>(null)
  const [reason, setReason] = useState('')
  const slot = db.slot.find((s) => s.slot_id === slotId)
  const daySlots = days.find(([k]) => k === activeDay)?.[1] ?? []
  const pending = me?.account_status !== 'active'

  const step = (n: number, title: string) => (
    <div className="mb-4 flex items-center gap-3">
      <span className="grid size-8 place-items-center rounded-xl bg-gradient-to-br from-navy to-navy-700 font-display text-sm font-bold text-gold shadow-lg shadow-navy/20 dark:from-gold dark:to-gold dark:text-navy-950">{n}</span>
      <h2 className="text-xl font-semibold">{title}</h2>
    </div>
  )

  return (
    <div>
      <PageHeader eyebrow={<><Sparkles className="size-3.5 text-gold" />Online appointment booking</>} title="Book a visit" description="Choose the kind of care you need, then pick a time that works for you. Times are shown in Manila time." />
      <PendingPatientBanner />
      <div className="grid gap-8 lg:grid-cols-[1fr_340px]">
        <div className="space-y-10">
          <section>
            {step(1, 'What kind of care?')}
            <div className="grid gap-4 sm:grid-cols-3">
              {providers.map((p) => {
                const I = careIcon[p.provider_type as keyof typeof careIcon]
                const active = p.provider_id === provider
                return (
                  <button key={p.provider_id} onClick={() => { setProvider(p.provider_id); setSlotId(null); setDay(null) }}
                    className={cx('group relative cursor-pointer overflow-hidden rounded-2xl border bg-surface text-left transition duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-navy/10', active ? 'border-transparent ring-2 ring-gold shadow-xl shadow-gold/15' : 'border-line')}>
                    <div className="relative aspect-[16/10] overflow-hidden">
                      <img src={bookingImage(p)} alt="" className={cx('h-full w-full object-cover object-[center_20%] transition duration-700 group-hover:scale-110', !active && 'saturate-[0.85]')} />
                      <div className="absolute inset-0 bg-gradient-to-t from-navy-950/70 to-transparent" />
                      <span className={cx('absolute bottom-3 left-3 grid size-9 place-items-center rounded-xl transition', active ? 'bg-gold text-navy-950' : 'bg-white/90 text-navy')}><I className="size-[18px]" /></span>
                      {active && <span className="animate-rise absolute top-3 right-3 grid size-7 place-items-center rounded-full bg-gold text-navy-950 shadow-lg"><Check className="size-4" strokeWidth={3} /></span>}
                    </div>
                    <div className="p-4">
                      <p className="font-semibold">{p.specialization}</p>
                      <p className="text-sm text-muted">{providerName(p.provider_id)}</p>
                    </div>
                  </button>
                )
              })}
            </div>
          </section>

          <section>
            {step(2, 'Pick a day and time')}
            {days.length === 0 ? (
              <Card><Empty icon={Clock} title="No open slots right now" text="Try another provider or check again later." /></Card>
            ) : (
              <>
                <div className="no-scrollbar -mx-1 mb-5 flex gap-2 overflow-x-auto px-1 pt-1 pb-3">
                  {days.map(([k, list]) => {
                    const d = new Date(list[0].start_time)
                    const active = k === activeDay
                    return (
                      <button key={k} onClick={() => { setDay(k); setSlotId(null) }}
                        className={cx('w-[78px] shrink-0 cursor-pointer rounded-2xl border px-2 py-3 text-center transition duration-300', active ? 'border-transparent bg-gradient-to-b from-[#ffe04d] to-gold text-navy-950 shadow-lg shadow-gold/30 -translate-y-0.5' : 'border-line bg-surface hover:-translate-y-0.5 hover:border-navy/30 hover:shadow-md')}>
                        <span className="block text-xs font-semibold opacity-70">{d.toLocaleDateString('en-PH', { weekday: 'short' })}</span>
                        <span className="block font-display text-2xl font-bold">{d.getDate()}</span>
                        <span className="block text-[11px] opacity-70">{list.length} open</span>
                      </button>
                    )
                  })}
                </div>
                {(['Morning', 'Afternoon'] as const).map((part) => {
                  const list = daySlots.filter((s) => (new Date(s.start_time).getHours() < 12) === (part === 'Morning'))
                  if (!list.length) return null
                  return (
                    <div key={part} className="mb-5">
                      <p className="mb-2 text-[13px] font-semibold text-muted">{part}</p>
                      <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
                        {list.map((s) => (
                          <button key={s.slot_id} onClick={() => setSlotId(s.slot_id)}
                            className={cx('cursor-pointer rounded-xl border py-2.5 text-sm font-semibold transition duration-200', slotId === s.slot_id ? 'scale-[1.03] border-transparent bg-gradient-to-b from-navy-700 to-navy text-white shadow-lg shadow-navy/30 dark:from-gold dark:to-gold dark:text-navy-950' : 'border-line bg-surface hover:-translate-y-0.5 hover:border-navy/40 hover:bg-tint')}>
                            {fmtTime(s.start_time)}
                          </button>
                        ))}
                      </div>
                    </div>
                  )
                })}
              </>
            )}
          </section>

          <section>
            {step(3, 'Tell us what’s going on')}
            <Textarea rows={4} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="For example: fever and sore throat since yesterday" />
            <div className="mt-3 flex flex-wrap gap-2">
              {['Fever or flu-like symptoms', 'Medical certificate', 'Annual physical exam', 'Dental check-up', 'Follow-up visit'].map((t) => (
                <button key={t} onClick={() => setReason(t)} className={cx('cursor-pointer rounded-full border px-3 py-1.5 text-[13px] font-medium transition', reason === t ? 'border-navy bg-navy text-white dark:border-gold dark:bg-gold dark:text-navy-950' : 'border-line bg-surface text-muted hover:-translate-y-px hover:border-navy/30 hover:text-ink')}>{t}</button>
              ))}
            </div>
          </section>
        </div>

        <aside className="lg:sticky lg:top-24 lg:self-start">
          <Card className="overflow-hidden">
            <div className="relative overflow-hidden bg-navy p-6 text-white dark:bg-navy-900">
              <div className="pointer-events-none absolute -top-16 -right-10 size-40 rounded-full bg-gold/25 blur-2xl" />
              <p className="relative text-[13px] font-medium text-white/60">Your visit</p>
              {slot ? (
                <div key={slot.slot_id} className="animate-blur-in relative">
                  <p className="mt-1 font-display text-xl font-bold">{fmtDay(slot.start_time)}</p>
                  <p className="font-semibold text-gold">{fmtTime(slot.start_time)} – {fmtTime(slot.end_time)}</p>
                </div>
              ) : <p className="relative mt-1 font-display text-xl font-bold text-white/50">Pick a time</p>}
            </div>
            <div className="space-y-3 p-6 text-sm">
              <p className="flex items-center gap-3"><Stethoscope className="size-4 text-muted" />{provider ? providerName(provider) : '—'}</p>
              <p className="flex items-center gap-3"><MapPin className="size-4 text-muted" />{slot?.room_id ? `${roomById.get(slot.room_id)?.building}, ${roomById.get(slot.room_id)?.room_number}` : 'Health Services Center'}</p>
              <p className="flex items-center gap-3"><Wallet className="size-4 text-muted" />{db.patient.find((p) => p.patient_id === me!.user_id)?.affiliation === 'student' ? 'Eligible clinic charges may post to your tuition' : 'Ask the clinic about applicable fees'}</p>
              <Button size="lg" variant="accent" className="mt-3 w-full" disabled={!slot || !reason.trim() || pending}
                onClick={() => run(async () => { await actions.bookAppointment(slot!.slot_id, reason); go('appointments') }, 'Visit booked.')}>
                Confirm booking
              </Button>
              {pending && <p className="text-center text-xs text-muted">Booking unlocks once your account is verified.</p>}
            </div>
          </Card>
        </aside>
      </div>
    </div>
  )
}
