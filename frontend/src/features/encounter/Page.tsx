import { useState } from 'react'
import {
AlertOctagon,Check,CheckCircle2,FileHeart,Lock,Pill,Plus,
Search,Send,Star,Trash2,Activity
} from 'lucide-react'
import { ActionButton, Avatar, Button, Card, Empty, Field, Input, Modal, PageHeader, SectionTitle, Select, Textarea, cx } from '../../components/ui'
import { age, fmtDate, fmtDateTime } from '../../data/format'
import { useLookups, useStore } from '../../data/store'
import type { MedicalRecord, ReferralStatus } from '../../data/types'
import { useNav } from '../../nav'
import { VitalsGrid } from '../visit-record/VitalsGrid'

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
