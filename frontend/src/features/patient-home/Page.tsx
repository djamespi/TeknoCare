import { CalendarCheck, CalendarPlus, FileHeart, HeartPulse, MapPin, Plus, ShieldAlert, Stethoscope, Wallet, Syringe, Thermometer, Gauge, Weight, CircleCheck } from 'lucide-react'
import { Avatar, Button, Card, Empty, PageHeader, Reveal, SectionTitle, Sparkline, Stat, Status, cx } from '../../components/ui'
import { clinicStatus, fmtTime, peso, relative } from '../../data/format'
import { useStore } from '../../data/store'
import { useNav } from '../../nav'
import { usePatientData } from '../../data/usePatientData'
import { PendingPatientBanner } from '../../components/PendingPatientBanner'
import { bookingImage, careIcon } from '../book-visit/bookingPhotos'

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

      <PendingPatientBanner />

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
                <img src={bookingImage(p)} alt="" className="absolute inset-0 h-full w-full object-cover transition duration-700 ease-out group-hover:scale-110" />
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
