import { useMemo, useState } from 'react'
import {
  AlertTriangle, CalendarCheck, CalendarPlus, Check, Clock, FileHeart, GraduationCap, HeartPulse, MapPin, Phone, Plus, ShieldAlert,
  Smile, Star, Stethoscope, Trash2, UserRound, Wallet, Hourglass, Syringe, Thermometer, Gauge, Weight, Sparkles, CircleCheck, Pill, Send, Users, Cake,
} from 'lucide-react'
import physicianImg from '../assets/service-physician.jpg'
import nurseImg from '../assets/service-nurse.jpg'
import dentalImg from '../assets/service-dental.jpg'
import { Avatar, Badge, Button, Card, Empty, Field, Input, Modal, PageHeader, Reveal, SectionTitle, Select, Sparkline, Stat, Status, Tabs, Textarea, cx } from '../components/ui'
import { age, clinicStatus, dayKey, fmtDate, fmtDateTime, fmtDay, fmtTime, peso, relative } from '../data/format'
import { useLookups, useStore } from '../data/store'
import type { Affiliation, Severity } from '../data/types'
import { useNav } from '../nav'

function usePatientData() {
  const { db, me } = useStore()
  const L = useLookups()
  const pid = me!.user_id
  const appts = db.appointment
    .filter((a) => a.patient_id === pid)
    .map((a) => ({ ...a, slot: L.slotById.get(a.slot_id)! }))
    .sort((a, b) => a.slot.start_time.localeCompare(b.slot.start_time))
  const records = db.medical_record.filter((r) => r.patient_id === pid && r.status === 'finalized').sort((a, b) => b.visited_at.localeCompare(a.visited_at))
  return { pid, appts, records, patient: L.patientById.get(pid), ...L }
}

function PendingBanner() {
  const { me } = useStore()
  if (me?.account_status !== 'pending') return null
  return (
    <div className="animate-rise mb-8 flex gap-4 rounded-2xl border border-gold/50 bg-gradient-to-r from-gold-100 to-white p-5 text-[#4a3b00] shadow-lg shadow-gold/10 dark:from-gold/10 dark:to-transparent dark:text-gold-100">
      <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-gold text-navy-950"><Hourglass className="size-5" /></span>
      <div>
        <p className="font-semibold">Your account is being verified</p>
        <p className="mt-0.5 text-sm opacity-80">The clinic confirms your school ID before you can book visits. This usually takes less than a day. Walk-ins are always welcome.</p>
      </div>
    </div>
  )
}

function DateBlock({ iso, muted }: { iso: string; muted?: boolean }) {
  const d = new Date(iso)
  return (
    <div className={cx('grid w-14 shrink-0 place-items-center rounded-xl py-2 text-center', muted ? 'bg-raised text-muted' : 'bg-navy text-white dark:bg-navy-700')}>
      <span className="text-[11px] font-semibold opacity-75">{d.toLocaleDateString('en-PH', { month: 'short' })}</span>
      <span className="font-display text-xl leading-none font-bold">{d.getDate()}</span>
    </div>
  )
}

export const careImage = { physician: physicianImg, nurse: nurseImg, dentist: dentalImg }

function LiveDot({ on = true }: { on?: boolean }) {
  return (
    <span className="relative flex size-2">
      {on && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-70" />}
      <span className={cx('relative inline-flex size-2 rounded-full', on ? 'bg-emerald-400' : 'bg-white/40')} />
    </span>
  )
}

export function PatientHome() {
  const { me, db, demo } = useStore()
  const { go } = useNav()
  const { appts, records, patient, providerName, roomById, providerById, pid } = usePatientData()
  const next = appts.find((a) => a.status === 'booked' && new Date(a.slot.end_time) > new Date())
  const allergies = db.patient_allergy.filter((a) => a.patient_id === pid)
  const contact = db.emergency_contact.find((c) => c.patient_id === pid && c.is_primary)
  const totalCharges = db.student_charge.filter((c) => db.medical_record.find((r) => r.record_id === c.record_id)?.patient_id === pid && c.status !== 'voided').reduce((s, c) => s + c.amount, 0)
  const activeRx = db.prescription.filter((p) => p.status === 'issued' && records.some((r) => r.record_id === p.record_id)).length
  const vitals = db.vital_sign.filter((v) => records.some((r) => r.record_id === v.record_id)).sort((a, b) => a.recorded_at.localeCompare(b.recorded_at))
  const series = (k: 'systolic_mmhg' | 'pulse_bpm' | 'weight_kg' | 'temperature_c') => vitals.map((v) => v[k]).filter((x): x is number => x != null)
  const last = vitals[vitals.length - 1]
  const hour = new Date().getHours()
  const greet = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'
  const status = demo ? clinicStatus() : { open: false, label: 'View available clinic times' }
  const providers = db.provider.filter((p) => p.eligible && p.provider_type !== 'unverified')

  const quick = [
    { icon: CalendarPlus, label: 'Book a visit', to: 'book' },
    { icon: FileHeart, label: 'Health records', to: 'records' },
    { icon: HeartPulse, label: 'Health profile', to: 'health' },
    { icon: Wallet, label: 'Clinic charges', to: 'billing' },
  ]

  return (
    <div>
      <PageHeader
        eyebrow={<><LiveDot on={status.open} />{status.label}</>}
        title={<>{greet}, <span className="text-shine">{me!.fname}</span></>}
        description="How are you feeling today? Your visits, records and clinic charges, all in one place."
        action={<Button icon={CalendarPlus} variant="accent" size="lg" onClick={() => go('book')}>Book a visit</Button>}
      >
        <div className="grid gap-4 lg:grid-cols-[1.55fr_1fr]">
          <div className="animate-rise relative overflow-hidden rounded-3xl bg-white/[0.07] p-6 ring-1 ring-white/12 backdrop-blur-xl sm:p-7" style={{ animationDelay: '200ms' }}>
            <div className="pointer-events-none absolute -top-20 -right-16 size-56 rounded-full bg-gold/20 blur-3xl" />
            {next ? (
              <div className="relative flex flex-col gap-6 sm:flex-row sm:items-center">
                <div className="grid w-24 shrink-0 place-items-center rounded-2xl bg-gold py-3 text-navy-950 shadow-xl shadow-gold/20">
                  <span className="text-xs font-bold">{new Date(next.slot.start_time).toLocaleDateString('en-PH', { month: 'short' })}</span>
                  <span className="font-display text-4xl leading-none font-bold">{new Date(next.slot.start_time).getDate()}</span>
                  <span className="text-xs font-semibold">{new Date(next.slot.start_time).toLocaleDateString('en-PH', { weekday: 'short' })}</span>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="flex items-center gap-2 text-sm text-white/60">Your next visit <span className="rounded-full bg-gold/15 px-2 py-0.5 text-xs font-semibold text-gold">{relative(next.slot.start_time)}</span></p>
                  <p className="mt-1 font-display text-2xl font-bold text-white">{fmtTime(next.slot.start_time)} – {fmtTime(next.slot.end_time)}</p>
                  <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-sm text-white/75">
                    <span className="flex items-center gap-2"><Stethoscope className="size-4 text-gold" />{providerName(next.slot.provider_id)}</span>
                    {next.slot.room_id && <span className="flex items-center gap-2"><MapPin className="size-4 text-gold" />{roomById.get(next.slot.room_id)?.room_number}</span>}
                  </div>
                  <p className="mt-3 truncate text-sm text-white/55">“{next.reason_for_visit}”</p>
                </div>
                <Button variant="glass" onClick={() => go('appointments')}>Manage</Button>
              </div>
            ) : (
              <div className="relative">
                <p className="text-sm text-white/60">No upcoming visits</p>
                <p className="mt-1 max-w-md font-display text-2xl font-bold text-white">Feeling under the weather? There are open slots this week.</p>
                <Button variant="accent" className="mt-5" icon={CalendarPlus} onClick={() => go('book')}>Find a time</Button>
              </div>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            {quick.map(({ icon: I, label, to }, i) => (
              <button key={to} onClick={() => go(to)} style={{ animationDelay: `${260 + i * 60}ms` }}
                className="animate-rise group flex cursor-pointer flex-col justify-between rounded-2xl bg-white/[0.06] p-4 text-left ring-1 ring-white/10 backdrop-blur-md transition duration-300 hover:-translate-y-1 hover:bg-white/[0.11] hover:ring-gold/40">
                <span className="grid size-10 place-items-center rounded-xl bg-white/10 text-gold transition duration-300 group-hover:scale-110 group-hover:bg-gold group-hover:text-navy-950"><I className="size-5" /></span>
                <span className="mt-6 text-sm font-semibold text-white">{label}</span>
              </button>
            ))}
          </div>
        </div>
      </PageHeader>

      <PendingBanner />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[
          <Stat key="a" icon={CalendarCheck} label="Upcoming visits" value={appts.filter((a) => a.status === 'booked').length} hint="Booked with the clinic" />,
          <Stat key="b" icon={FileHeart} label="Health records" value={records.length} hint="Finalized visits" />,
          <Stat key="c" icon={Syringe} label="Active prescriptions" value={activeRx} hint="Issued by your providers" />,
          <Stat key="d" icon={Wallet} label="Visit charges" value={patient?.affiliation === 'student' ? totalCharges : 'Free'} format={peso} tone="gold" hint={patient?.affiliation === 'student' ? 'Recorded clinic charges' : 'University affiliation'} />,
        ].map((c, i) => <Reveal key={i} delay={i * 80}>{c}</Reveal>)}
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        <Reveal>
          <Card className="h-full p-6">
            <SectionTitle title="Health snapshot" description={last ? `From your visit ${relative(last.recorded_at)}` : 'Vitals from your clinic visits appear here'} action={<Button size="sm" variant="ghost" onClick={() => go('records')}>All records</Button>} />
            {last ? (
              <div className="grid grid-cols-2 gap-3">
                {[
                  { icon: Gauge, label: 'Blood pressure', value: last.systolic_mmhg ? `${last.systolic_mmhg}/${last.diastolic_mmhg}` : '—', unit: 'mmHg', data: series('systolic_mmhg') },
                  { icon: HeartPulse, label: 'Pulse', value: last.pulse_bpm ?? '—', unit: 'bpm', data: series('pulse_bpm') },
                  { icon: Thermometer, label: 'Temperature', value: last.temperature_c ?? '—', unit: '°C', data: series('temperature_c') },
                  { icon: Weight, label: 'Weight', value: last.weight_kg ?? '—', unit: 'kg', data: series('weight_kg') },
                ].map(({ icon: I, label, value, unit, data }) => (
                  <div key={label} className="rounded-2xl bg-raised/70 p-4 ring-1 ring-line/50 transition hover:ring-navy/20">
                    <div className="flex items-center gap-1.5 text-xs text-muted"><I className="size-3.5" />{label}</div>
                    <div className="mt-1 flex items-end justify-between gap-3">
                      <p className="font-display text-2xl font-bold">{value}<span className="ml-1 font-sans text-xs font-medium text-muted">{unit}</span></p>
                      <div className="w-20 pb-1"><Sparkline data={data} /></div>
                    </div>
                  </div>
                ))}
              </div>
            ) : <Empty icon={HeartPulse} title="No vitals yet" text="Your first visit will start your health timeline." />}
          </Card>
        </Reveal>
        <Reveal delay={100}>
          <Card className="h-full p-6">
            <SectionTitle title="Safety information" action={<Button size="sm" variant="ghost" onClick={() => go('health')}>Edit</Button>} />
            <p className="mb-2 text-[13px] font-semibold text-muted">Allergies</p>
            {allergies.length ? (
              <ul className="space-y-2">
                {allergies.map((a) => (
                  <li key={a.allergy_id} className="flex items-center gap-3 rounded-xl bg-raised/70 px-3.5 py-2.5">
                    <ShieldAlert className={cx('size-4 shrink-0', a.severity === 'severe' ? 'text-red-500' : a.severity === 'moderate' ? 'text-orange-500' : 'text-gold-600')} />
                    <span className="flex-1 text-sm font-semibold">{a.allergen}</span>
                    <Status value={a.severity} />
                  </li>
                ))}
              </ul>
            ) : <p className="flex items-center gap-2 text-sm text-muted"><CircleCheck className="size-4 text-muted" />No allergies documented</p>}
            <p className="mt-5 mb-2 text-[13px] font-semibold text-muted">Emergency contact</p>
            {contact ? (
              <div className="flex items-center gap-3">
                <Avatar name={contact.full_name} size="sm" />
                <div className="min-w-0"><p className="text-sm font-semibold">{contact.full_name} <span className="font-normal text-muted">· {contact.relationship}</span></p><p className="text-xs text-muted">{contact.phone_number}</p></div>
              </div>
            ) : <Button size="sm" variant="outline" icon={Plus} onClick={() => go('health')}>Add a contact</Button>}
          </Card>
        </Reveal>
      </div>

      <Reveal className="mt-14">
        <SectionTitle title="Care at the Health Services Center" description="Licensed professionals on campus, a short walk from your class." />
        <div className="grid gap-4 md:grid-cols-3">
          {providers.map((p, i) => (
            <Reveal key={p.provider_id} delay={i * 90}>
              <button onClick={() => go(`book/${p.provider_id}`)} className="group relative block aspect-[4/5] w-full cursor-pointer overflow-hidden rounded-3xl text-left shadow-xl shadow-navy/10 sm:aspect-[4/4.4]">
                <img src={careImage[p.provider_type as keyof typeof careImage]} alt="" className="absolute inset-0 h-full w-full object-cover transition duration-700 ease-out group-hover:scale-110" />
                <div className="absolute inset-0 bg-gradient-to-t from-navy-950 via-navy-950/40 to-transparent transition duration-500 group-hover:via-navy-950/55" />
                <div className="absolute inset-x-0 bottom-0 p-6 text-white">
                  <span className="mb-3 inline-grid size-10 place-items-center rounded-xl bg-gold text-navy-950 transition duration-500 group-hover:-translate-y-1">{(() => { const I = careIcon[p.provider_type as keyof typeof careIcon]; return <I className="size-5" /> })()}</span>
                  <p className="font-display text-2xl font-bold">{p.specialization}</p>
                  <p className="text-sm text-white/70">{providerName(p.provider_id)}</p>
                  <p className="mt-4 max-h-0 overflow-hidden text-sm font-semibold text-gold opacity-0 transition-all duration-500 group-hover:max-h-8 group-hover:opacity-100">Book with {providerById.get(p.provider_id)?.provider_type === 'nurse' ? 'the nurse' : 'this provider'}</p>
                </div>
              </button>
            </Reveal>
          ))}
        </div>
      </Reveal>

      <Reveal className="mt-14">
        <SectionTitle title="Recent visits" action={records.length > 0 && <Button variant="ghost" size="sm" onClick={() => go('records')}>See all</Button>} />
        {records.length === 0 ? <Card><Empty icon={FileHeart} title="No visits yet" text="Your visit summary becomes available after your clinician finalizes it." /></Card> : (
          <ol className="relative space-y-3 before:absolute before:top-4 before:bottom-4 before:left-[27px] before:w-px before:bg-gradient-to-b before:from-gold before:via-line before:to-transparent">
            {records.slice(0, 4).map((r, i) => (
              <Reveal key={r.record_id} delay={i * 70}>
                <li className="relative flex gap-4">
                  <span className="relative z-10 mt-3 grid size-[54px] shrink-0 place-items-center rounded-2xl border border-line bg-surface text-center shadow-sm">
                    <span className="text-[10px] leading-none font-semibold text-muted">{new Date(r.visited_at).toLocaleDateString('en-PH', { month: 'short' })}</span>
                    <span className="font-display text-lg leading-none font-bold">{new Date(r.visited_at).getDate()}</span>
                  </span>
                  <button onClick={() => go(`record/${r.record_id}`)} className="spotlight flex-1 cursor-pointer rounded-2xl border border-line bg-surface p-4 text-left transition duration-300 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-navy/5">
                    <p className="font-semibold">{r.chief_complaint}</p>
                    <p className="mt-0.5 line-clamp-1 text-sm text-muted">{providerName(r.provider_id)} · {r.treatment_plan}</p>
                  </button>
                </li>
              </Reveal>
            ))}
          </ol>
        )}
      </Reveal>
    </div>
  )
}

const careIcon = { physician: Stethoscope, nurse: HeartPulse, dentist: Smile }

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
      <PendingBanner />
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
                      <img src={careImage[p.provider_type as keyof typeof careImage]} alt="" className={cx('h-full w-full object-cover transition duration-700 group-hover:scale-110', !active && 'saturate-[0.85]')} />
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
              <div className="hero-grid pointer-events-none absolute inset-0 opacity-60" />
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

export function Appointments() {
  const { actions, db } = useStore()
  const { go, run } = useNav()
  const { appts, providerName, roomById, providerById } = usePatientData()
  const [tab, setTab] = useState<'upcoming' | 'past' | 'canceled'>('upcoming')
  const [confirm, setConfirm] = useState<number | null>(null)
  const groups = {
    upcoming: appts.filter((a) => a.status === 'booked' || a.status === 'checked_in'),
    past: appts.filter((a) => a.status === 'completed' || a.status === 'no_show').reverse(),
    canceled: appts.filter((a) => a.status === 'canceled').reverse(),
  }
  const list = groups[tab]
  return (
    <div>
      <PageHeader title="Appointments" description="Everything you’ve booked with the clinic, past and upcoming." action={<Button icon={CalendarPlus} variant="accent" onClick={() => go('book')}>Book a visit</Button>}
        stats={[{ icon: CalendarCheck, label: 'Upcoming', value: groups.upcoming.length }, { icon: CircleCheck, label: 'Completed', value: groups.past.filter((a) => a.status === 'completed').length }, { icon: Clock, label: 'Canceled', value: groups.canceled.length }]} />
      <div className="mb-5">
        <Tabs value={tab} onChange={setTab} items={[{ value: 'upcoming', label: 'Upcoming', count: groups.upcoming.length }, { value: 'past', label: 'Past', count: groups.past.length }, { value: 'canceled', label: 'Canceled', count: groups.canceled.length }]} />
      </div>
      <Card className="divide-y divide-line">
        {list.length === 0 && <Empty icon={CalendarCheck} title={tab === 'upcoming' ? 'Nothing scheduled' : 'Nothing here yet'} text={tab === 'upcoming' ? 'Book a visit and it will show up here.' : undefined} />}
        {list.map((a, idx) => {
          const rec = db.medical_record.find((r) => r.appointment_id === a.appointment_id && r.status === 'finalized')
          const room = a.slot.room_id ? roomById.get(a.slot.room_id) : null
          return (
            <div key={a.appointment_id} className={cx('animate-rise relative flex flex-col gap-4 p-5 transition hover:bg-raised/40 sm:flex-row sm:items-center', tab === 'upcoming' && idx === 0 && 'bg-gold-100/40 dark:bg-gold/5')} style={{ animationDelay: `${idx * 50}ms` }}>
              {tab === 'upcoming' && idx === 0 && <span className="absolute top-4 bottom-4 left-0 w-1 rounded-r-full bg-gold" />}
              <DateBlock iso={a.slot.start_time} muted={tab !== 'upcoming'} />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-semibold">{fmtTime(a.slot.start_time)} · {providerById.get(a.slot.provider_id)?.specialization}</p>
                  <Status value={a.status} />
                </div>
                <p className="mt-0.5 text-sm text-muted">{providerName(a.slot.provider_id)}{room && ` · ${room.building}, ${room.room_number}`}</p>
                <p className="mt-1 text-sm">{a.reason_for_visit}</p>
                {a.canceled_at && <p className="mt-1 text-xs text-muted">Canceled {fmtDateTime(a.canceled_at)}</p>}
              </div>
              <div className="flex gap-2">
                {rec && <Button variant="outline" size="sm" icon={FileHeart} onClick={() => go(`record/${rec.record_id}`)}>View record</Button>}
                {a.can_cancel && <>
                  <Button variant="outline" size="sm" onClick={() => window.location.assign(`/appointments/${a.appointment_id}/reschedule/`)}>Reschedule</Button>
                  <Button variant="danger" size="sm" onClick={() => setConfirm(a.appointment_id)}>Cancel</Button>
                </>}
              </div>
            </div>
          )
        })}
      </Card>
      <Modal open={confirm != null} onClose={() => setConfirm(null)} title="Cancel this visit?" description="Your slot will be released so another student can book it.">
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setConfirm(null)}>Keep visit</Button>
          <Button onClick={async () => { if (await run(() => actions.cancelAppointment(confirm!), 'Visit canceled.')) setConfirm(null) }}>Yes, cancel</Button>
        </div>
      </Modal>
    </div>
  )
}

export function Records() {
  const { go } = useNav()
  const { db } = useStore()
  const { records, providerName, dxById } = usePatientData()
  return (
    <div>
      <PageHeader title="Health records" description="Notes, diagnoses and prescriptions from your finalized clinic visits."
        stats={[{ icon: FileHeart, label: 'Visits on record', value: records.length }, { icon: Pill, label: 'Medicines prescribed', value: records.reduce((n, r) => n + db.prescription.filter((p) => p.record_id === r.record_id).reduce((m, p) => m + db.prescription_item.filter((i) => i.prescription_id === p.prescription_id).length, 0), 0) }, { icon: Send, label: 'Referrals', value: db.referral.filter((f) => records.some((r) => r.record_id === f.record_id)).length }]} />
      {records.length === 0 ? <Card><Empty icon={FileHeart} title="No records yet" text="Records appear here once your provider finalizes a visit." /></Card> : (
        <div className="grid gap-4 md:grid-cols-2">
          {records.map((r, i) => {
            const dx = db.record_diagnosis.filter((d) => d.record_id === r.record_id)
            const items = db.prescription.filter((p) => p.record_id === r.record_id).flatMap((p) => db.prescription_item.filter((i) => i.prescription_id === p.prescription_id))
            return (
              <Reveal key={r.record_id} delay={(i % 2) * 90}>
              <button onClick={() => go(`record/${r.record_id}`)} className="spotlight group relative h-full w-full cursor-pointer overflow-hidden rounded-2xl border border-line bg-surface p-6 text-left shadow-[0_8px_24px_-12px_rgba(0,20,60,0.08)] transition duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-navy/10">
                <span className="absolute inset-x-0 top-0 h-1 origin-left scale-x-0 bg-gradient-to-r from-navy via-navy-700 to-gold transition duration-500 group-hover:scale-x-100" />
                <div className="mb-4 flex items-center justify-between">
                  <p className="text-sm text-muted">{fmtDate(r.visited_at, { weekday: 'short', month: 'long', day: 'numeric', year: 'numeric' })}</p>
                  <FileHeart className="size-5 text-brand opacity-40 transition group-hover:opacity-100" />
                </div>
                <h3 className="text-xl font-semibold">{r.chief_complaint}</h3>
                <p className="mt-1 text-sm text-muted">{providerName(r.provider_id)}</p>
                <div className="mt-5 flex flex-wrap gap-1.5">
                  {dx.map((d) => <Badge key={d.record_diagnosis_id} tone="navy">{dxById.get(d.diagnosis_id)?.description}</Badge>)}
                  {items.length > 0 && <Badge tone="gold">{items.length} medicine{items.length > 1 ? 's' : ''}</Badge>}
                </div>
              </button>
              </Reveal>
            )
          })}
        </div>
      )}
    </div>
  )
}

export function HealthProfile({ patientId }: { patientId?: number }) {
  const { db, me, actions } = useStore()
  const { run } = useNav()
  const pid = patientId ?? me!.user_id
  const p = db.patient.find((x) => x.patient_id === pid)!
  const allergies = db.patient_allergy.filter((a) => a.patient_id === pid)
  const contacts = db.emergency_contact.filter((c) => c.patient_id === pid)
  const [info, setInfo] = useState({ date_of_birth: p.date_of_birth ?? '', department_id: String(p.department_id ?? ''), affiliation: p.affiliation ?? '', medical_history_summary: p.medical_history_summary ?? '' })
  const [contactOpen, setContactOpen] = useState(false)
  const [ct, setCt] = useState({ full_name: '', relationship: '', phone_number: '', is_primary: false })

  return (
    <div>
      {!patientId && <PageHeader title="Health profile" description="Keeping this current helps clinic staff care for you safely, especially in an emergency."
        stats={[{ icon: Cake, label: 'Age', value: age(p.date_of_birth) ?? 0, hint: p.date_of_birth ? fmtDate(p.date_of_birth) : 'Add your birthday' }, { icon: ShieldAlert, label: 'Allergies on file', value: allergies.length }, { icon: Users, label: 'Emergency contacts', value: contacts.length }]} />}
      <div className="grid gap-5 lg:grid-cols-[1.3fr_1fr]">
        <Card className="p-6">
          <SectionTitle title="Personal health information" />
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Date of birth"><Input type="date" disabled={!!patientId} value={info.date_of_birth} onChange={(e) => setInfo({ ...info, date_of_birth: e.target.value })} /></Field>
            <Field label="Affiliation" hint="Changes are re-verified by the clinic">
              <Select disabled value={info.affiliation} onChange={(e) => setInfo({ ...info, affiliation: e.target.value as Affiliation })}>
                <option value="">Awaiting review</option><option value="student">Student</option><option value="faculty">Faculty</option><option value="staff">Staff</option>
              </Select>
            </Field>
            <Field label="Department" className="sm:col-span-2">
              <Select disabled value={info.department_id} onChange={(e) => setInfo({ ...info, department_id: e.target.value })}>
                <option value="">Not set</option>
                {db.department.map((d) => <option key={d.department_id} value={d.department_id}>{d.name}</option>)}
              </Select>
            </Field>
            <Field label="Medical history" className="sm:col-span-2" hint="Conditions, surgeries, maintenance medicines">
              <Textarea readOnly rows={4} value={info.medical_history_summary} onChange={(e) => setInfo({ ...info, medical_history_summary: e.target.value })} />
            </Field>
          </div>
          <div className="mt-5 flex justify-end">
            {!patientId && <Button icon={Check} onClick={() => run(() => actions.updateBirthDate(info.date_of_birth || null), 'Health information saved.')}>Save birth date</Button>}
          </div>
        </Card>

        <div className="space-y-5">
          <Card className="p-6">
            <SectionTitle title="Allergies" />
            {allergies.length === 0 ? <p className="text-sm text-muted">No allergies documented.</p> : (
              <ul className="space-y-2">
                {allergies.map((a) => (
                  <li key={a.allergy_id} className="group flex items-start gap-3 rounded-xl bg-raised p-3.5">
                    <ShieldAlert className={cx('mt-0.5 size-4 shrink-0', a.severity === 'severe' ? 'text-red-500' : a.severity === 'moderate' ? 'text-orange-500' : 'text-gold-600')} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2"><p className="font-semibold">{a.allergen}</p><Status value={a.severity} /></div>
                      {a.reaction && <p className="text-sm text-muted">{a.reaction}</p>}
                    </div>

                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card className="p-6">
            <SectionTitle title="Emergency contacts" action={!patientId && <Button size="sm" variant="outline" icon={Plus} onClick={() => setContactOpen(true)}>Add</Button>} />
            {contacts.length === 0 ? <p className="text-sm text-muted">Add someone we can reach if you need help.</p> : (
              <ul className="space-y-2">
                {contacts.map((c) => (
                  <li key={c.contact_id} className="group flex items-center gap-3 rounded-xl bg-raised p-3.5">
                    <Avatar name={c.full_name} size="sm" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2"><p className="font-semibold">{c.full_name}</p>{c.is_primary && <Badge tone="navy">Primary</Badge>}</div>
                      <p className="flex items-center gap-1.5 text-sm text-muted">{c.relationship} · <Phone className="size-3" />{c.phone_number}</p>
                    </div>
                    {!c.is_primary && <button aria-label="Make primary" title="Make primary" onClick={() => run(() => actions.setPrimaryContact(c.contact_id))} className="cursor-pointer rounded-lg p-1.5 text-muted opacity-0 transition group-hover:opacity-100 hover:bg-surface hover:text-brand focus:opacity-100"><Star className="size-4" /></button>}
                    <button aria-label={`Remove ${c.full_name}`} onClick={() => run(() => actions.removeContact(c.contact_id))} className="cursor-pointer rounded-lg p-1.5 text-muted opacity-0 transition group-hover:opacity-100 hover:bg-surface hover:text-red-600 focus:opacity-100"><Trash2 className="size-4" /></button>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>

      <Modal open={contactOpen} onClose={() => setContactOpen(false)} title="Add emergency contact">
        <div className="grid grid-cols-2 gap-4">
          <Field label="Full name" className="col-span-2"><Input value={ct.full_name} onChange={(e) => setCt({ ...ct, full_name: e.target.value })} /></Field>
          <Field label="Relationship"><Input value={ct.relationship} onChange={(e) => setCt({ ...ct, relationship: e.target.value })} placeholder="Mother" /></Field>
          <Field label="Phone"><Input value={ct.phone_number} onChange={(e) => setCt({ ...ct, phone_number: e.target.value })} placeholder="+63 9xx xxx xxxx" /></Field>
          <label className="col-span-2 flex cursor-pointer items-center gap-2 text-sm"><input type="checkbox" className="size-4 accent-[#002870]" checked={ct.is_primary} onChange={(e) => setCt({ ...ct, is_primary: e.target.checked })} /> Make this my primary contact</label>
          <Button className="col-span-2" onClick={async () => { if (await run(() => actions.addContact( { ...ct, relationship: ct.relationship || 'Other' }), 'Contact added.')) { setContactOpen(false); setCt({ full_name: '', relationship: '', phone_number: '', is_primary: false }) } }}>Save contact</Button>
        </div>
      </Modal>
    </div>
  )
}

export function Billing() {
  const { db, me } = useStore()
  const { go } = useNav()
  const { termById, recordById } = useLookups()
  const patient = db.patient.find((p) => p.patient_id === me!.user_id)
  const charges = db.student_charge.filter((c) => recordById.get(c.record_id)?.patient_id === me!.user_id).sort((a, b) => b.created_at.localeCompare(a.created_at))
  const live = charges.filter((c) => c.status !== 'voided')
  const total = live.reduce((s, c) => s + c.amount, 0)
  const posted = live.filter((c) => c.status === 'posted').reduce((s, c) => s + c.amount, 0)

  if ((patient?.affiliation === 'faculty' || patient?.affiliation === 'staff') && !charges.length) {
    return (
      <div>
        <PageHeader title="Clinic charges" description="Faculty and staff clinic visits are free." />
        <Card className="relative overflow-hidden p-12 text-center">
          <div className="dot-grid pointer-events-none absolute inset-0 [mask-image:radial-gradient(circle_at_center,#000,transparent_70%)]" />
          <div className="animate-float relative mx-auto mb-5 grid size-16 place-items-center rounded-2xl bg-gradient-to-br from-[#ffe04d] to-gold text-navy-950 shadow-xl shadow-gold/30"><UserRound className="size-7" /></div>
          <h2 className="relative text-3xl font-bold">Your visits are free</h2>
          <p className="relative mx-auto mt-2 max-w-md text-muted">There are no charges from prior student visits on your account.</p>
        </Card>
      </div>
    )
  }
  return (
    <div>
      <PageHeader title="Clinic charges" description="View charges for visits recorded with a student affiliation. Posted indicates a tuition charge. Payment is handled outside TeknoCare."
        stats={[{ icon: Wallet, label: 'Recorded charges', value: total, format: peso }, { icon: GraduationCap, label: 'Posted to tuition', value: posted, format: peso }, { icon: Clock, label: 'Awaiting posting', value: total - posted, format: peso }]} />
      <Card className="overflow-hidden">
        {charges.length === 0 ? <Empty icon={Wallet} title="No charges" text="You haven’t been charged for any clinic visits." /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-line bg-raised/60 text-left text-[13px] text-muted">
                <tr><th className="px-5 py-3 font-semibold">Charge</th><th className="px-5 py-3 font-semibold">Visit</th><th className="px-5 py-3 font-semibold">Term</th><th className="px-5 py-3 font-semibold">Status</th><th className="px-5 py-3 text-right font-semibold">Amount</th></tr>
              </thead>
              <tbody className="divide-y divide-line">
                {charges.map((c) => {
                  const r = recordById.get(c.record_id)
                  const t = termById.get(c.term_id)
                  return (
                    <tr key={c.charge_id} className="hover:bg-raised/40">
                      <td className="px-5 py-4"><p className="font-mono text-xs font-semibold">{c.charge_code}</p><p className="text-xs text-muted">{c.billing_reference ?? 'Not yet billed'}</p></td>
                      <td className="px-5 py-4"><button onClick={() => r && go(`record/${r.record_id}`)} className="cursor-pointer text-left font-medium hover:text-brand">{r?.chief_complaint}</button><p className="text-xs text-muted">{r && fmtDate(r.visited_at)}</p></td>
                      <td className="px-5 py-4 text-muted">{t?.semester}, {t?.academic_year}</td>
                      <td className="px-5 py-4"><Status value={c.status} />{c.void_reason && <p className="mt-1 text-xs text-muted">{c.void_reason}</p>}</td>
                      <td className={cx('px-5 py-4 text-right font-semibold', c.status === 'voided' && 'text-muted line-through')}>{peso(c.amount)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      <p className="mt-4 flex items-center gap-2 text-xs text-muted"><AlertTriangle className="size-3.5" />Questions about a charge? Visit the clinic office with your charge code.</p>
    </div>
  )
}
