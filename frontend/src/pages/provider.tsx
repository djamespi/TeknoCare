import { useMemo, useState } from 'react'
import {
  AlertOctagon, CalendarPlus, Check, CheckCircle2, ClipboardPlus, GraduationCap, Clock, FilePen, FileHeart, Lock, Pill, Plus,
  Search, Send, Star, Stethoscope, Trash2, UserCheck, UserX, Users, Activity, Library, MapPin,
} from 'lucide-react'
import { ActionButton, Avatar, Badge, Button, Card, Empty, Field, Input, Modal, PageHeader, SectionTitle, Select, Stat, Status, Tabs, Textarea, cx } from '../components/ui'
import { age, dayKey, fmtDate, fmtDateTime, fmtTime, peso } from '../data/format'
import { useLookups, useStore } from '../data/store'
import type { MedicalRecord, ReferralStatus } from '../data/types'
import { useNav } from '../nav'
import { HealthProfile } from './patient'
import { RecordDetail, VitalsGrid } from './records'

function weekdays(fromOffset: number, count: number) {
  const out: Date[] = []
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  d.setDate(d.getDate() + fromOffset)
  while (out.length < count) {
    if (d.getDay() !== 0 && d.getDay() !== 6) out.push(new Date(d))
    d.setDate(d.getDate() + 1)
  }
  return out
}

export function Today() {
  const { db, me, actions } = useStore()
  const { go, run } = useNav()
  const { name, slotById, patientById, deptById, roomById } = useLookups()
  const days = useMemo(() => weekdays(-2, 8), [])
  const todayKey = dayKey(new Date().toISOString())
  const [day, setDay] = useState(todayKey)
  const pid = me!.user_id
  const appts = db.appointment
    .map((a) => ({ ...a, slot: slotById.get(a.slot_id)! }))
    .filter((a) => a.slot.provider_id === pid && dayKey(a.slot.start_time) === day && a.status !== 'canceled')
    .sort((a, b) => a.slot.start_time.localeCompare(b.slot.start_time))
  const drafts = db.medical_record.filter((r) => r.status === 'draft' && (r.can_edit || r.can_record_vitals))
  const openVisit = async (appointment_id: number) => {
    let id = 0
    if (await run(async () => { id = await actions.startRecord(appointment_id) })) go(`encounter/${id}`)
  }

  return (
    <div>
      <PageHeader
        eyebrow={<><Stethoscope className="size-3.5 text-gold" />{db.provider.find((p) => p.provider_id === pid)?.specialization}</>}
        title={<>Good day, <span className="text-shine">{db.provider.find((p) => p.provider_id === pid)?.provider_type === 'nurse' ? 'Nurse' : 'Dr.'} {me!.lname}</span></>}
        description="Your patient queue. Check patients in as they arrive, then open the visit to chart."
        action={<Button variant="glass" icon={CalendarPlus} onClick={() => go('schedule')}>Manage slots</Button>}
        stats={[
          { icon: Users, label: day === todayKey ? 'Patients today' : 'Patients this day', value: appts.length },
          { icon: UserCheck, label: 'Waiting', value: appts.filter((a) => a.status === 'checked_in').length },
          { icon: CheckCircle2, label: 'Seen', value: appts.filter((a) => a.status === 'completed').length },
          { icon: FilePen, label: 'Unfinished charts', value: drafts.length },
        ]}
      >
        <div className="no-scrollbar -mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
          {days.map((d, i) => {
            const k = dayKey(d.toISOString())
            const count = db.appointment.filter((a) => a.status !== 'canceled' && slotById.get(a.slot_id)?.provider_id === pid && dayKey(slotById.get(a.slot_id)!.start_time) === k).length
            const active = k === day
            return (
              <button key={k} onClick={() => setDay(k)} style={{ animationDelay: `${300 + i * 40}ms` }}
                className={cx('animate-rise min-w-[92px] shrink-0 cursor-pointer rounded-2xl px-3.5 py-3 text-left ring-1 transition duration-300', active ? 'bg-gold text-navy-950 shadow-xl shadow-gold/20 ring-gold' : 'bg-white/[0.06] text-white ring-white/10 backdrop-blur-md hover:-translate-y-0.5 hover:bg-white/[0.1]')}>
                <span className="block text-xs font-semibold opacity-70">{k === todayKey ? 'Today' : d.toLocaleDateString('en-PH', { weekday: 'short' })}</span>
                <span className="block font-display text-lg font-bold">{d.toLocaleDateString('en-PH', { month: 'short', day: 'numeric' })}</span>
                <span className="block text-[11px] opacity-70">{count} patient{count === 1 ? '' : 's'}</span>
              </button>
            )
          })}
        </div>
      </PageHeader>

      <SectionTitle title={day === todayKey ? 'Today’s queue' : new Date(`${day}T00:00`).toLocaleDateString('en-PH', { weekday: 'long', month: 'long', day: 'numeric' })} description={appts.length ? `${appts.filter((a) => a.status === 'booked' || a.status === 'checked_in').length} still to see` : undefined} />
      {appts.length === 0 ? <Card><Empty icon={Stethoscope} title="No patients booked" text="Open slots for this day appear to patients on the booking page." /></Card> : (
        <ol className="relative space-y-3 before:absolute before:top-6 before:bottom-6 before:left-[87px] before:hidden before:w-px before:bg-gradient-to-b before:from-gold before:via-line before:to-line md:before:block">
          {appts.map((a, idx) => {
            const p = patientById.get(a.patient_id)
            const rec = db.medical_record.find((r) => r.appointment_id === a.appointment_id)
            const allergies = db.patient_allergy.filter((x) => x.patient_id === a.patient_id)
            const room = a.slot.room_id ? roomById.get(a.slot.room_id) : null
            const nextUp = appts.find((x) => x.status === 'checked_in') ?? appts.find((x) => x.status === 'booked')
            const isNext = nextUp?.appointment_id === a.appointment_id
            const done = a.status === 'completed' || a.status === 'no_show'
            return (
              <li key={a.appointment_id} className="animate-rise relative flex flex-col gap-3 md:flex-row md:items-stretch md:gap-6" style={{ animationDelay: `${idx * 60}ms` }}>
                <div className="flex w-20 shrink-0 items-center gap-3 md:flex-col md:items-end md:justify-center md:gap-0 md:text-right">
                  <p className={cx('font-display text-lg font-bold', done && 'text-muted')}>{fmtTime(a.slot.start_time)}</p>
                  {room && <p className="text-xs text-muted">{room.room_number}</p>}
                </div>
                <span className={cx('absolute top-1/2 left-[81px] z-10 hidden size-3.5 -translate-y-1/2 rounded-full ring-4 ring-canvas md:block', isNext ? 'bg-gold' : done ? 'bg-emerald-500' : 'bg-line')}>
                  {isNext && <span className="absolute inset-0 animate-ping rounded-full bg-gold/70" />}
                </span>
                <div className={cx('spotlight flex flex-1 flex-col gap-4 rounded-2xl border bg-surface p-4 shadow-[0_8px_24px_-12px_rgba(0,20,60,0.08)] transition duration-300 hover:-translate-y-0.5 md:ml-4 md:flex-row md:items-center', isNext ? 'border-gold/70 ring-4 ring-gold/15' : 'border-line', done && 'opacity-75')}>
                  <div className="flex min-w-0 flex-1 items-center gap-3">
                    <Avatar name={name(a.patient_id)} />
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <button onClick={() => go(`patients/${a.patient_id}`)} className="cursor-pointer font-semibold hover:text-brand">{name(a.patient_id)}</button>
                        <Status value={a.status} />
                        {isNext && <Badge tone="gold">Up next</Badge>}
                        {allergies.length > 0 && <Badge tone="red"><AlertOctagon className="size-3" />{allergies.length} allerg{allergies.length > 1 ? 'ies' : 'y'}</Badge>}
                      </div>
                      <p className="truncate text-sm text-muted"><span className="capitalize">{p?.affiliation}</span>{p?.department_id && ` · ${deptById.get(p.department_id)?.code}`}{age(p?.date_of_birth ?? null) != null && ` · ${age(p!.date_of_birth)} yrs`} · {a.reason_for_visit}</p>
                    </div>
                  </div>
                  <div className="flex shrink-0 flex-wrap gap-2">
                    {a.status === 'booked' && (
                      <>
                        <Button size="sm" variant="ghost" icon={UserX} onClick={() => run(() => actions.setAppointmentStatus(a.appointment_id, 'no_show'), 'Marked as missed.')}>Missed</Button>
                        <Button size="sm" variant="outline" icon={UserCheck} onClick={() => run(() => actions.setAppointmentStatus(a.appointment_id, 'checked_in'), `${name(a.patient_id)} checked in.`)}>Check in</Button>
                      </>
                    )}
                    {(a.status === 'checked_in') && <Button size="sm" variant={isNext ? 'accent' : 'primary'} icon={ClipboardPlus} onClick={() => openVisit(a.appointment_id)}>{rec ? 'Continue visit' : 'Start visit'}</Button>}
                    {a.status === 'completed' && rec && <Button size="sm" variant="outline" icon={FileHeart} onClick={() => go(`encounter/${rec.record_id}`)}>View chart</Button>}
                  </div>
                </div>
              </li>
            )
          })}
        </ol>
      )}

      {drafts.length > 0 && (
        <div className="mt-10">
          <SectionTitle title="Unfinished charts" description="Finalize these so patients can see their records." />
          <div className="grid gap-3 md:grid-cols-2">
            {drafts.map((r) => (
              <button key={r.record_id} onClick={() => go(`encounter/${r.record_id}`)} className="spotlight flex cursor-pointer items-center gap-4 rounded-2xl border border-gold/50 bg-gradient-to-r from-gold-100/70 to-surface p-4 text-left transition duration-300 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-gold/10 dark:from-gold/10">
                <span className="grid size-10 place-items-center rounded-xl bg-gold text-navy-950"><FilePen className="size-5" /></span>
                <div className="min-w-0 flex-1"><p className="font-semibold">{name(r.patient_id)}</p><p className="truncate text-sm text-muted">{r.chief_complaint} · {fmtDateTime(r.visited_at)}</p></div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function NoteField({ record, field, label, placeholder, rows = 3 }: { record: MedicalRecord; field: 'chief_complaint' | 'symptoms' | 'examination_notes' | 'treatment_plan'; label: string; placeholder?: string; rows?: number }) {
  const { actions } = useStore()
  const { run } = useNav()
  const [v, setV] = useState(record[field] ?? '')
  const locked = !record.can_edit
  return (
    <Field label={label}>
      <Textarea rows={rows} value={v} disabled={locked} placeholder={placeholder} onChange={(e) => setV(e.target.value)} onBlur={() => v !== (record[field] ?? '') && run(() => actions.updateRecord(record.record_id, { [field]: field === 'chief_complaint' ? v : v || null }))} />
    </Field>
  )
}

const crossReactive: Record<string, string[]> = { penicillin: ['amoxicillin'], sulfonamides: ['sulfamethoxazole'], nsaid: ['ibuprofen', 'mefenamic acid'] }

export function Encounter({ recordId }: { recordId: number }) {
  const { db, actions } = useStore()
  const { go, run } = useNav()
  const { name, patientById, deptById, dxById, medById } = useLookups()
  const r = db.medical_record.find((x) => x.record_id === recordId)
  const [vOpen, setVOpen] = useState(false)
  const [rxOpen, setRxOpen] = useState(false)
  const [refOpen, setRefOpen] = useState(false)
  const [finOpen, setFinOpen] = useState(false)
  const [dxQ, setDxQ] = useState('')
  const [vit, setVit] = useState<Record<string, string>>({})
  const [rx, setRx] = useState({ medication_id: '', dose: '', route: 'Oral', frequency: '', duration_days: '', quantity: '', quantity_unit: '', instructions: '' })
  const [ref, setRef] = useState({ destination: '', reason: '' })
  if (!r) return <Empty icon={FileHeart} title="Chart not found" />

  const locked = !r.can_edit
  const p = patientById.get(r.patient_id)!
  const allergies = db.patient_allergy.filter((a) => a.patient_id === r.patient_id)
  const contact = db.emergency_contact.find((c) => c.patient_id === r.patient_id && c.is_primary)
  const vitals = db.vital_sign.filter((v) => v.record_id === recordId).sort((a, b) => b.recorded_at.localeCompare(a.recorded_at))
  const dx = db.record_diagnosis.filter((d) => d.record_id === recordId)
  const rxs = db.prescription.filter((x) => x.record_id === recordId && x.status !== 'canceled')
  const items = rxs.flatMap((x) => db.prescription_item.filter((i) => i.prescription_id === x.prescription_id))
  const refs = db.referral.filter((x) => x.record_id === recordId)
  const past = db.medical_record.filter((x) => x.patient_id === r.patient_id && x.record_id !== recordId && x.status === 'finalized').sort((a, b) => b.visited_at.localeCompare(a.visited_at))
  const dxResults = dxQ.trim() ? db.diagnosis.filter((d) => `${d.code} ${d.description}`.toLowerCase().includes(dxQ.toLowerCase())).slice(0, 6) : []
  const selectedMed = medById.get(Number(rx.medication_id))
  const medWarning = selectedMed && allergies.find((a) => {
    const al = a.allergen.toLowerCase()
    const med = selectedMed.generic_name.toLowerCase()
    return med.includes(al) || (crossReactive[al] ?? []).includes(med)
  })
  const num = (k: string) => (vit[k] ? Number(vit[k]) : null)

  return (
    <div>
      <PageHeader
        back={{ label: 'Back to queue', onClick: () => go('today') }}
        eyebrow={<><span className="capitalize">{r.affiliation_at_visit ?? 'Patient'}</span> · {db.user.find((u) => u.user_id === r.patient_id)?.school_id}{age(p.date_of_birth) != null && ` · ${age(p.date_of_birth)} yrs`}</>}
        title={name(r.patient_id)}
        description={<>Visit started {fmtDateTime(r.visited_at)} · Record #{r.record_id}</>}
        action={r.status === 'finalized' ? <span className="inline-flex items-center gap-2 rounded-full bg-emerald-400/15 px-4 py-2 text-sm font-semibold text-emerald-300 ring-1 ring-emerald-400/25"><Lock className="size-4" />Finalized {r.finalized_at && fmtDate(r.finalized_at)}</span> : r.can_finalize && <Button variant="accent" size="lg" icon={CheckCircle2} onClick={() => setFinOpen(true)}>Finalize visit</Button>}
      />

      {allergies.length > 0 && (
        <div className="mb-6 flex gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-red-800 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-200">
          <AlertOctagon className="mt-0.5 size-5 shrink-0" />
          <div className="text-sm"><p className="font-semibold">Allergies on file</p><p>{allergies.map((a) => `${a.allergen} (${a.severity}${a.reaction ? `: ${a.reaction}` : ''})`).join(' · ')}</p></div>
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
        <div className="space-y-5">
          <Card className="p-6">
            <SectionTitle title="Subjective" description="What the patient tells you" />
            <div className="space-y-4">
              <NoteField record={r} field="chief_complaint" label="Chief complaint" rows={2} />
              <NoteField record={r} field="symptoms" label="Symptoms" placeholder="Onset, duration, severity, associated symptoms" />
            </div>
          </Card>

          <Card className="p-6">
            <SectionTitle title="Vital signs" action={r.can_record_vitals && <Button size="sm" variant="outline" icon={Activity} onClick={() => setVOpen(true)}>{vitals.length ? 'Record again' : 'Record vitals'}</Button>} />
            <VitalsGrid v={vitals[0]} />
            {vitals[0] && <p className="mt-3 text-xs text-muted">Taken {fmtDateTime(vitals[0].recorded_at)} by {name(vitals[0].recorded_by_user_id)}{vitals.length > 1 && ` · ${vitals.length - 1} earlier reading${vitals.length > 2 ? 's' : ''}`}</p>}
          </Card>

          <Card className="p-6">
            <SectionTitle title="Assessment" />
            <div className="space-y-4">
              <NoteField record={r} field="examination_notes" label="Examination findings" rows={4} />
              <div>
                <p className="mb-1.5 text-[13px] font-semibold">Diagnoses</p>
                <div className="space-y-2">
                  {dx.map((d) => {
                    const x = dxById.get(d.diagnosis_id)
                    return (
                      <div key={d.record_diagnosis_id} className="flex items-center gap-3 rounded-xl bg-raised px-4 py-3">
                        <ActionButton disabled={locked} title={d.is_primary ? 'Primary diagnosis' : 'Make primary'} onClick={() => run(() => actions.setPrimaryDiagnosis(d.record_diagnosis_id))} className="cursor-pointer disabled:cursor-default">
                          <Star className={cx('size-4', d.is_primary ? 'fill-gold text-gold' : 'text-muted')} />
                        </ActionButton>
                        <span className="font-mono text-xs font-semibold text-brand">{x?.code}</span>
                        <span className="flex-1 text-sm">{x?.description}</span>
                        {!locked && <ActionButton aria-label="Remove diagnosis" onClick={() => run(() => actions.removeDiagnosis(d.record_diagnosis_id))} className="cursor-pointer rounded-lg p-1 text-muted hover:text-red-600"><Trash2 className="size-4" /></ActionButton>}
                      </div>
                    )
                  })}
                  {!locked && (
                    <div className="relative">
                      <Search className="pointer-events-none absolute top-3.5 left-3.5 size-4 text-muted" />
                      <Input className="pl-10" value={dxQ} onChange={(e) => setDxQ(e.target.value)} placeholder="Search ICD-10 code or description" />
                      {dxResults.length > 0 && (
                        <div className="animate-rise mt-2 overflow-hidden rounded-xl border border-line bg-surface shadow-xl shadow-navy/10">
                          {dxResults.map((d) => (
                            <ActionButton key={d.diagnosis_id} onClick={async () => {
                              if (await run(() => actions.addDiagnosis(recordId, d.diagnosis_id))) {
                                setDxQ(current => current === dxQ ? '' : current)
                              }
                            }} className="flex w-full cursor-pointer items-center gap-3 px-4 py-2.5 text-left text-sm hover:bg-raised">
                              <span className="w-16 font-mono text-xs font-semibold text-brand">{d.code}</span>{d.description}
                            </ActionButton>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                  {locked && dx.length === 0 && <p className="text-sm text-muted">No diagnoses recorded.</p>}
                </div>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <SectionTitle title="Plan" />
            <div className="space-y-5">
              <NoteField record={r} field="treatment_plan" label="Treatment plan and advice" rows={4} />
              <div>
                <div className="mb-2 flex items-center justify-between"><p className="text-[13px] font-semibold">Prescription</p>{r.can_prescribe && <Button size="sm" variant="outline" icon={Plus} onClick={() => setRxOpen(true)}>Add medicine</Button>}</div>
                {items.length === 0 ? <p className="text-sm text-muted">No medicines added.</p> : (
                  <div className="space-y-2">
                    {items.map((i) => {
                      const m = medById.get(i.medication_id)
                      return (
                        <div key={i.item_id} className="flex items-center gap-3 rounded-xl border border-line p-3.5">
                          <Pill className="size-4 shrink-0 text-brand" />
                          <div className="min-w-0 flex-1"><p className="text-sm font-semibold">{m?.generic_name} {m?.strength}</p><p className="text-xs text-muted">{i.dose} {i.route.toLowerCase()} · {i.frequency} · {i.duration_days} days · {i.quantity} {i.quantity_unit}</p></div>
                          {r.can_prescribe && rxs.some(rx => rx.prescription_id === i.prescription_id && rx.status === "draft") && <ActionButton aria-label="Remove medicine" onClick={() => run(() => actions.removePrescriptionItem(i.item_id))} className="cursor-pointer rounded-lg p-1 text-muted hover:text-red-600"><Trash2 className="size-4" /></ActionButton>}
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
              <div>
                {r.can_prescribe && rxs.filter(p => p.status === 'draft').map(p => <div key={p.prescription_id} className="mb-4 flex flex-wrap gap-2">
                <Button size="sm" onClick={() => { if (window.confirm('Issue this prescription?')) return run(() => actions.prescriptionStatus(p.prescription_id, 'issue'), 'Prescription issued.') }}>Issue prescription</Button>
                <Button size="sm" variant="outline" onClick={() => { if (window.confirm('Discard this draft?')) return run(() => actions.prescriptionStatus(p.prescription_id, 'discard'), 'Draft discarded.') }}>Discard draft</Button>
              </div>)}
              <div className="mb-2 flex items-center justify-between"><p className="text-[13px] font-semibold">Referrals</p>{r.can_refer && <Button size="sm" variant="outline" icon={Send} onClick={() => setRefOpen(true)}>Refer out</Button>}</div>
                {refs.length === 0 ? <p className="text-sm text-muted">No referrals.</p> : refs.map((f) => (
                  <div key={f.referral_id} className="mb-2 flex items-center gap-3 rounded-xl border border-line p-3.5">
                    <Send className="size-4 shrink-0 text-brand" />
                    <div className="min-w-0 flex-1"><p className="text-sm font-semibold">{f.destination}</p><p className="text-xs text-muted">{f.reason}</p></div>
                    <Select className="h-9 w-32 text-xs" value={f.status} disabled={f.status !== 'pending'} onChange={(e) => run(() => actions.setReferralStatus(f.referral_id, e.target.value as ReferralStatus))}>
                      {['pending', 'sent', 'accepted', 'completed'].map((s) => <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>)}
                    </Select>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>

        <aside className="space-y-5 lg:sticky lg:top-24 lg:self-start">
          <Card className="p-6">
            <div className="mb-5 flex items-center gap-3">
              <Avatar name={name(r.patient_id)} size="lg" />
              <div><p className="font-display text-lg font-bold">{name(r.patient_id)}</p><p className="text-sm text-muted">{db.user.find((u) => u.user_id === r.patient_id)?.school_id}</p></div>
            </div>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-xl bg-raised p-3"><dt className="text-xs text-muted">Age</dt><dd className="font-semibold">{age(p.date_of_birth) ?? '—'}</dd></div>
              <div className="rounded-xl bg-raised p-3"><dt className="text-xs text-muted">At visit</dt><dd className="font-semibold capitalize">{r.affiliation_at_visit ?? '—'}</dd></div>
              <div className="col-span-2 rounded-xl bg-raised p-3"><dt className="text-xs text-muted">Department</dt><dd className="font-semibold">{p.department_id ? deptById.get(p.department_id)?.name : '—'}</dd></div>
            </dl>
            <p className="mt-5 mb-1 text-[13px] font-semibold">Medical history</p>
            <p className="text-sm text-muted">{p.medical_history_summary ?? 'None provided.'}</p>
            {contact && (<><p className="mt-5 mb-1 text-[13px] font-semibold">Emergency contact</p><p className="text-sm">{contact.full_name} <span className="text-muted">({contact.relationship})</span></p><p className="text-sm text-muted">{contact.phone_number}</p></>)}
            <Button variant="outline" size="sm" className="mt-5 w-full" onClick={() => go(`patients/${r.patient_id}`)}>Open patient file</Button>
          </Card>
          <Card className="p-6">
            <p className="mb-3 text-[13px] font-semibold">Previous visits</p>
            {past.length === 0 ? <p className="text-sm text-muted">First visit.</p> : past.slice(0, 4).map((x) => (
              <button key={x.record_id} onClick={() => go(`patients/${r.patient_id}/record/${x.record_id}`)} className="mb-1 block w-full cursor-pointer rounded-lg p-2 -mx-2 text-left hover:bg-raised">
                <p className="text-sm font-medium">{x.chief_complaint}</p><p className="text-xs text-muted">{fmtDate(x.visited_at)}</p>
              </button>
            ))}
          </Card>
        </aside>
      </div>

      <Modal open={vOpen} onClose={() => setVOpen(false)} title="Record vital signs" wide>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[['temperature_c', 'Temp (°C)', '36.5'], ['systolic_mmhg', 'Systolic', '120'], ['diastolic_mmhg', 'Diastolic', '80'], ['pulse_bpm', 'Pulse (bpm)', '72'], ['respiratory_rate', 'Resp. rate', '16'], ['oxygen_saturation_pct', 'SpO₂ (%)', '98'], ['height_cm', 'Height (cm)', '165'], ['weight_kg', 'Weight (kg)', '60']].map(([k, l, ph]) => (
            <Field key={k} label={l}><Input type="number" step="0.1" placeholder={ph} value={vit[k] ?? ''} onChange={(e) => setVit({ ...vit, [k]: e.target.value })} /></Field>
          ))}
        </div>
        <Button className="mt-6 w-full" onClick={async () => {
          if (await run(() => actions.saveVitals(recordId, { temperature_c: num('temperature_c'), systolic_mmhg: num('systolic_mmhg'), diastolic_mmhg: num('diastolic_mmhg'), pulse_bpm: num('pulse_bpm'), respiratory_rate: num('respiratory_rate'), oxygen_saturation_pct: num('oxygen_saturation_pct'), height_cm: num('height_cm'), weight_kg: num('weight_kg') }), 'Vitals saved.')) { setVOpen(false); setVit({}) }
        }}>Save vitals</Button>
      </Modal>

      <Modal open={rxOpen} onClose={() => setRxOpen(false)} title="Add medicine" wide>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Medicine" className="col-span-2">
            <Select value={rx.medication_id} onChange={(e) => { const m = medById.get(Number(e.target.value)); setRx({ ...rx, medication_id: e.target.value, quantity_unit: m ? m.dosage_form.toLowerCase() + 's' : rx.quantity_unit }) }}>
              <option value="">Choose from formulary</option>
              {db.medication.filter((m) => m.is_active).map((m) => <option key={m.medication_id} value={m.medication_id}>{m.generic_name} {m.strength} · {m.dosage_form}</option>)}
            </Select>
          </Field>
          {medWarning && <div className="col-span-2 flex gap-2 rounded-xl bg-red-50 p-3 text-sm text-red-800 dark:bg-red-500/10 dark:text-red-200"><AlertOctagon className="size-4 shrink-0" />Patient has a recorded {medWarning.severity} allergy to {medWarning.allergen}. Review before prescribing.</div>}
          <Field label="Dose"><Input value={rx.dose} onChange={(e) => setRx({ ...rx, dose: e.target.value })} /></Field>
          <Field label="Route"><Select value={rx.route} onChange={(e) => setRx({ ...rx, route: e.target.value })}>{['Oral', 'Topical', 'Inhalation', 'Oral rinse', 'Sublingual', 'Ophthalmic'].map((x) => <option key={x}>{x}</option>)}</Select></Field>
          <Field label="Frequency" className="col-span-2"><Input value={rx.frequency} onChange={(e) => setRx({ ...rx, frequency: e.target.value })} placeholder="Enter the prescribed frequency" /></Field>
          <Field label="Duration (days)"><Input type="number" value={rx.duration_days} onChange={(e) => setRx({ ...rx, duration_days: e.target.value })} /></Field>
          <div className="grid grid-cols-[1fr_1.2fr] gap-2">
            <Field label="Quantity"><Input type="number" value={rx.quantity} onChange={(e) => setRx({ ...rx, quantity: e.target.value })} /></Field>
            <Field label="Unit"><Input value={rx.quantity_unit} onChange={(e) => setRx({ ...rx, quantity_unit: e.target.value })} /></Field>
          </div>
          <Field label="Instructions for patient" className="col-span-2"><Textarea rows={2} value={rx.instructions} onChange={(e) => setRx({ ...rx, instructions: e.target.value })} /></Field>
          <Button className="col-span-2" disabled={!rx.medication_id || !rx.frequency || !rx.quantity} onClick={async () => {
            if (await run(() => actions.addPrescriptionItem(recordId, { medication_id: Number(rx.medication_id), dose: rx.dose, route: rx.route, frequency: rx.frequency, duration_days: Number(rx.duration_days), quantity: Number(rx.quantity), quantity_unit: rx.quantity_unit, instructions: rx.instructions || null }))) {

            setRxOpen(false); setRx({ ...rx, medication_id: '', frequency: '', quantity: '', instructions: '' })
            }
          }}>Add to prescription</Button>
        </div>
      </Modal>

      <Modal open={refOpen} onClose={() => setRefOpen(false)} title="Refer to another facility">
        <div className="space-y-4">
          <Field label="Destination"><Input value={ref.destination} onChange={(e) => setRef({ ...ref, destination: e.target.value })} placeholder="Hospital, specialist or service" /></Field>
          <Field label="Reason"><Textarea value={ref.reason} onChange={(e) => setRef({ ...ref, reason: e.target.value })} /></Field>
          <Button className="w-full" onClick={async () => { if (await run(() => actions.addReferral(recordId, ref.destination, ref.reason), 'Referral created.')) { setRefOpen(false); setRef({ destination: '', reason: '' }) } }}>Create referral</Button>
        </div>
      </Modal>

      <Modal open={finOpen} onClose={() => setFinOpen(false)} title="Finalize this visit?" description="The record becomes read-only and visible to the patient. Draft prescriptions are issued.">
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-2 text-center text-sm">
            <div className="rounded-xl bg-raised p-3"><p className="font-display text-xl font-bold">{vitals.length ? 'Yes' : 'No'}</p><p className="text-xs text-muted">Vitals</p></div>
            <div className="rounded-xl bg-raised p-3"><p className="font-display text-xl font-bold">{dx.length}</p><p className="text-xs text-muted">Diagnoses</p></div>
            <div className="rounded-xl bg-raised p-3"><p className="font-display text-xl font-bold">{items.length}</p><p className="text-xs text-muted">Medicines</p></div>
          </div>
          <p className="rounded-xl bg-tint p-3 text-sm text-brand">Authorized clinic administrators handle student tuition charges in the charges workspace.</p>
          <Button className="w-full" icon={Check} onClick={async () => { if (await run(() => actions.finalizeRecord(recordId), 'Visit finalized.')) setFinOpen(false) }}>Finalize visit</Button>
        </div>
      </Modal>
    </div>
  )
}

export function Patients() {
  const { db } = useStore()
  const { go } = useNav()
  const { name, deptById } = useLookups()
  const [q, setQ] = useState('')
  const [aff, setAff] = useState('all')
  const rows = db.patient
    .map((p) => ({ p, u: db.user.find((u) => u.user_id === p.patient_id)! }))
    .filter(({ p, u }) => (aff === 'all' || p.affiliation === aff) && `${u.fname} ${u.lname} ${u.school_id} ${u.email}`.toLowerCase().includes(q.toLowerCase()))
  return (
    <div>
      <PageHeader title="Patients" description="Everyone registered with the clinic. Search by name, school ID or email."
        stats={[{ icon: Users, label: 'Registered', value: db.patient.length }, { icon: GraduationCap, label: 'Students', value: db.patient.filter((p) => p.affiliation === 'student').length }, { icon: AlertOctagon, label: 'With allergies', value: new Set(db.patient_allergy.map((a) => a.patient_id)).size }]} />
      <div className="mb-5 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1"><Search className="pointer-events-none absolute top-3.5 left-3.5 size-4 text-muted" /><Input className="pl-10" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by name, school ID or email" /></div>
        <Tabs value={aff} onChange={setAff} items={[{ value: 'all', label: 'All' }, { value: 'student', label: 'Students' }, { value: 'faculty', label: 'Faculty' }, { value: 'staff', label: 'Staff' }]} />
      </div>
      <Card className="divide-y divide-line">
        {rows.length === 0 && <Empty icon={Users} title="No matches" />}
        {rows.map(({ p, u }) => {
          const visits = db.medical_record.filter((r) => r.patient_id === p.patient_id).length
          const allergies = db.patient_allergy.filter((a) => a.patient_id === p.patient_id).length
          return (
            <button key={p.patient_id} onClick={() => go(`patients/${p.patient_id}`)} className="group flex w-full cursor-pointer items-center gap-4 p-4 text-left transition duration-200 hover:bg-raised/60">
              <Avatar name={name(u.user_id)} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2"><p className="font-semibold">{name(u.user_id)}</p>{u.account_status !== 'active' && <Status value={u.account_status} />}</div>
                <p className="truncate text-sm text-muted">{u.school_id} · <span className="capitalize">{p.affiliation}</span>{p.department_id && ` · ${deptById.get(p.department_id)?.code}`}</p>
              </div>
              <div className="hidden gap-2 sm:flex">
                {allergies > 0 && <Badge tone="red">{allergies} allerg{allergies > 1 ? 'ies' : 'y'}</Badge>}
                <Badge>{visits} visit{visits === 1 ? '' : 's'}</Badge>
              </div>
            </button>
          )
        })}
      </Card>
    </div>
  )
}

export function PatientFile({ patientId }: { patientId: number }) {
  const { db } = useStore()
  const { go } = useNav()
  const { name, providerName, slotById } = useLookups()
  const [tab, setTab] = useState<'visits' | 'profile' | 'appointments'>('visits')
  const u = db.user.find((x) => x.user_id === patientId)
  if (!u) return <Empty icon={Users} title="Patient not found" />
  const records = db.medical_record.filter((r) => r.patient_id === patientId).sort((a, b) => b.visited_at.localeCompare(a.visited_at))
  const appts = db.appointment.filter((a) => a.patient_id === patientId).map((a) => ({ ...a, slot: slotById.get(a.slot_id)! })).sort((a, b) => b.slot.start_time.localeCompare(a.slot.start_time))
  const profile = db.user_profile.find((x) => x.user_id === patientId)
  return (
    <div>
      <PageHeader
        back={{ label: 'All patients', onClick: () => go('patients') }}
        eyebrow={<>{u.school_id} · {u.email}{profile?.phone_number && ` · ${profile.phone_number}`}</>}
        title={<span className="flex items-center gap-4"><Avatar name={name(patientId)} tone="gold" size="lg" className="hidden sm:grid" />{name(patientId)}</span>}
        stats={[{ icon: FileHeart, label: 'Visits', value: records.length }, { icon: CalendarPlus, label: 'Appointments', value: appts.length }, { icon: AlertOctagon, label: 'Allergies', value: db.patient_allergy.filter((a) => a.patient_id === patientId).length }]}
      />
      <div className="mb-5"><Tabs value={tab} onChange={setTab} items={[{ value: 'visits', label: 'Visits', count: records.length }, { value: 'appointments', label: 'Appointments', count: appts.length }, { value: 'profile', label: 'Health profile' }]} /></div>
      {tab === 'visits' && (
        <Card className="divide-y divide-line">
          {records.length === 0 && <Empty icon={FileHeart} title="No visits yet" />}
          {records.map((r) => (
            <button key={r.record_id} onClick={() => go(r.status === 'draft' ? `encounter/${r.record_id}` : `patients/${patientId}/record/${r.record_id}`)} className="flex w-full cursor-pointer items-center gap-4 p-5 text-left hover:bg-raised/60">
              <div className="w-24 shrink-0 text-sm"><p className="font-semibold">{fmtDate(r.visited_at, { month: 'short', day: 'numeric' })}</p><p className="text-xs text-muted">{new Date(r.visited_at).getFullYear()}</p></div>
              <div className="min-w-0 flex-1"><p className="font-semibold">{r.chief_complaint}</p><p className="truncate text-sm text-muted">{providerName(r.provider_id)} · {r.treatment_plan ?? 'No plan yet'}</p></div>
              <Status value={r.status} />
            </button>
          ))}
        </Card>
      )}
      {tab === 'appointments' && (
        <Card className="divide-y divide-line">
          {appts.map((a) => (
            <div key={a.appointment_id} className="flex items-center gap-4 p-5">
              <div className="w-40 shrink-0 text-sm"><p className="font-semibold">{fmtDate(a.slot.start_time)}</p><p className="text-xs text-muted">{fmtTime(a.slot.start_time)}</p></div>
              <div className="min-w-0 flex-1"><p className="text-sm">{a.reason_for_visit}</p><p className="text-xs text-muted">{providerName(a.slot.provider_id)}</p></div>
              <Status value={a.status} />
            </div>
          ))}
        </Card>
      )}
      {tab === 'profile' && <HealthProfile patientId={patientId} />}
    </div>
  )
}

export function PatientRecord({ patientId, recordId }: { patientId: number; recordId: number }) {
  return <RecordDetail record_id={recordId} backTo={`patients/${patientId}`} backLabel="Patient file" />
}

export function Schedule() {
  const { db, me, actions } = useStore()
  const { run } = useNav()
  const { name, providerName, roomById, bookedSlots } = useLookups()
  const isAdmin = me!.user_type === 'admin'
  const [providerId, setProviderId] = useState(isAdmin ? db.provider.find(p => p.eligible)?.provider_id ?? 0 : me!.user_id)
  const [week, setWeek] = useState('0')
  const [open, setOpen] = useState(false)
  const defaultRoom = db.slot.find((s) => s.provider_id === providerId)?.room_id ?? db.clinic_room[0]?.room_id
  const [f, setF] = useState({ date: dayKey(new Date(Date.now() + 86_400_000 * 7).toISOString()), from: '08:00', to: '12:00', minutes: '30', room: String(defaultRoom ?? '') })
  const days = useMemo(() => {
    const d = new Date()
    d.setHours(0, 0, 0, 0)
    d.setDate(d.getDate() - ((d.getDay() + 6) % 7) + Number(week) * 7)
    return Array.from({ length: 5 }, (_, i) => new Date(d.getTime() + i * 86_400_000))
  }, [week])
  const apptBySlot = new Map(db.appointment.filter((a) => a.status !== 'canceled').map((a) => [a.slot_id, a]))
  const slots = db.slot.filter((s) => s.provider_id === providerId)

  return (
    <div>
      <PageHeader title={isAdmin ? 'Provider schedules' : 'Your schedule'} description="Open slots are bookable by patients. Select an open slot to close it, or a closed slot to reopen it." action={<Button variant="accent" icon={CalendarPlus} disabled={!providerId} onClick={() => setOpen(true)}>Publish slots</Button>}
        stats={(() => {
          const inWeek = slots.filter((s) => days.some((d) => dayKey(d.toISOString()) === dayKey(s.start_time)))
          const booked = inWeek.filter((s) => bookedSlots.has(s.slot_id)).length
          return [
            { icon: CalendarPlus, label: 'Slots this week', value: inWeek.length },
            { icon: UserCheck, label: 'Booked', value: booked },
            { icon: Clock, label: 'Utilization', value: inWeek.length ? Math.round((booked / inWeek.length) * 100) : 0, format: (n: number) => `${Math.round(n)}%` },
          ]
        })()} />
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Tabs value={week} onChange={setWeek} items={[{ value: '-1', label: 'Last week' }, { value: '0', label: 'This week' }, { value: '1', label: 'Next week' }, { value: '2', label: 'In 2 weeks' }]} />
        <div className="flex items-center gap-3">
          {isAdmin && (
            <Select className="w-64" value={providerId} onChange={(e) => setProviderId(Number(e.target.value))}>
              {!providerId && <option value={0}>No eligible providers</option>}{db.provider.filter(p => p.eligible).map((p) => <option key={p.provider_id} value={p.provider_id}>{providerName(p.provider_id)}</option>)}
            </Select>
          )}
        </div>
      </div>
      <div className="mb-4 flex flex-wrap gap-4 text-xs text-muted">
        <span className="flex items-center gap-1.5"><span className="size-3 rounded border border-line bg-surface" />Open</span>
        <span className="flex items-center gap-1.5"><span className="size-3 rounded bg-navy" />Booked</span>
        <span className="flex items-center gap-1.5"><span className="size-3 rounded bg-raised" />Closed</span>
      </div>
      <div className="grid gap-3 overflow-x-auto md:grid-cols-5">
        {days.map((d) => {
          const list = slots.filter((s) => dayKey(s.start_time) === dayKey(d.toISOString())).sort((a, b) => a.start_time.localeCompare(b.start_time))
          const isToday = dayKey(d.toISOString()) === dayKey(new Date().toISOString())
          return (
            <Card key={d.toISOString()} className={cx('animate-rise p-3', isToday && 'ring-2 ring-gold')}>
              <div className="mb-3 px-1">
                <p className="text-xs font-semibold text-muted">{d.toLocaleDateString('en-PH', { weekday: 'long' })}</p>
                <p className="font-display text-lg font-bold">{d.toLocaleDateString('en-PH', { month: 'short', day: 'numeric' })}</p>
              </div>
              {list.length === 0 ? <p className="px-1 py-6 text-center text-xs text-muted">No slots</p> : (
                <div className="space-y-1.5">
                  {list.map((s) => {
                    const a = apptBySlot.get(s.slot_id)
                    const past = new Date(s.start_time) < new Date()
                    return (
                      <ActionButton key={s.slot_id} disabled={!!a || past} onClick={() => run(() => actions.toggleSlot(s.slot_id), s.is_active ? 'Slot closed.' : 'Slot reopened.')}
                        title={a ? `${name(a.patient_id)}: ${a.reason_for_visit}` : undefined}
                        className={cx('flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-xs transition',
                          a ? 'bg-gradient-to-r from-navy to-navy-700 text-white shadow-sm shadow-navy/20 dark:from-navy-700 dark:to-navy-700' : s.is_active ? 'cursor-pointer border border-line bg-surface hover:translate-x-0.5 hover:border-gold hover:bg-gold-100/40' : 'cursor-pointer bg-raised text-muted line-through',
                          past && !a && 'opacity-45')}>
                        <span className="font-semibold">{fmtTime(s.start_time)}</span>
                        {a && <span className="truncate opacity-80">{name(a.patient_id).split(' ')[0]}</span>}
                      </ActionButton>
                    )
                  })}
                </div>
              )}
              {list.length > 0 && <p className="mt-3 px-1 text-[11px] text-muted"><MapPin className="mr-1 inline size-3" />{roomById.get(list[0].room_id ?? 0)?.room_number ?? 'No room'} · {list.filter((s) => bookedSlots.has(s.slot_id)).length}/{list.length} booked</p>}
            </Card>
          )
        })}
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title="Publish new slots" description={`For ${providerName(providerId)}. Choose an active room and a time range without conflicts.`}>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Date" className="col-span-2"><Input type="date" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} /></Field>
          <Field label="From"><Input type="time" value={f.from} onChange={(e) => setF({ ...f, from: e.target.value })} /></Field>
          <Field label="To"><Input type="time" value={f.to} onChange={(e) => setF({ ...f, to: e.target.value })} /></Field>
          <Field label="Slot length"><Select value={f.minutes} onChange={(e) => setF({ ...f, minutes: e.target.value })}><option value="15">15 minutes</option><option value="30">30 minutes</option><option value="60">1 hour</option></Select></Field>
          <Field label="Room"><Select value={f.room} onChange={(e) => setF({ ...f, room: e.target.value })}><option value="">No room</option>{db.clinic_room.filter((r) => r.is_active).map((r) => <option key={r.room_id} value={r.room_id}>{r.room_number}</option>)}</Select></Field>
          <Button className="col-span-2" icon={Clock} onClick={async () => {
            let n = 0
            if (await run(async () => { n = await actions.addSlots(providerId, f.room ? Number(f.room) : null, f.date, f.from, f.to, Number(f.minutes)) })) {
              setOpen(false)
              run(() => {}, n ? `Published ${n} slot${n > 1 ? 's' : ''}.` : 'Those times already exist.')
            }
          }}>Publish</Button>
        </div>
      </Modal>
    </div>
  )
}

export function Formulary() {
  const { db } = useStore()
  const [q, setQ] = useState('')
  const list = db.medication.filter((m) => `${m.generic_name} ${m.medication_code} ${m.dosage_form}`.toLowerCase().includes(q.toLowerCase()))
  return (
    <div>
      <PageHeader title="Formulary" description="Browse medication formulations used in clinic prescriptions."
        stats={[{ icon: Pill, label: 'Medicines', value: db.medication.length }, { icon: CheckCircle2, label: 'Active in catalog', value: db.medication.filter((m) => m.is_active).length }, { icon: Library, label: 'Dosage forms', value: new Set(db.medication.map((m) => m.dosage_form)).size }]} />
      <div className="relative mb-5"><Search className="pointer-events-none absolute top-3.5 left-3.5 size-4 text-muted" /><Input className="pl-10" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search medicines" /></div>
      {list.length === 0 ? <Card><Empty icon={Library} title="No medicines found" /></Card> : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {list.map((m) => (
            <Card key={m.medication_id} className={cx('group animate-rise flex items-center gap-4 p-4 transition duration-300 hover:-translate-y-0.5', !m.is_active && 'opacity-50')}>
              <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-navy to-navy-700 text-gold shadow-lg shadow-navy/20 transition duration-300 group-hover:rotate-6"><Pill className="size-5" /></span>
              <div className="min-w-0 flex-1"><p className="font-semibold">{m.generic_name}</p><p className="text-sm text-muted">{m.strength} · {m.dosage_form}</p></div>
              <span className="font-mono text-[11px] text-muted">{m.medication_code}</span>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
