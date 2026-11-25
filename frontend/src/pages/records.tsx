import { Activity, FileHeart, Gauge, HeartPulse, Pill, Ruler, Send, Thermometer, Weight, Wind } from 'lucide-react'
import { Badge, Card, Empty, PageHeader, Status } from '../components/ui'
import { fmtDate, fmtDateTime, peso } from '../data/format'
import { useLookups, useStore } from '../data/store'
import type { VitalSign } from '../data/types'
import { useNav } from '../nav'

export function VitalsGrid({ v }: { v: VitalSign | undefined }) {
  if (!v) return <p className="text-sm text-muted">No vitals recorded yet.</p>
  const bmi = v.height_cm && v.weight_kg ? (v.weight_kg / (v.height_cm / 100) ** 2).toFixed(1) : null
  const items = [
    { icon: Thermometer, label: 'Temperature', value: v.temperature_c, unit: '°C', warn: (v.temperature_c ?? 0) >= 37.8 },
    { icon: Gauge, label: 'Blood pressure', value: v.systolic_mmhg ? `${v.systolic_mmhg}/${v.diastolic_mmhg}` : null, unit: 'mmHg', warn: (v.systolic_mmhg ?? 0) >= 140 },
    { icon: HeartPulse, label: 'Pulse', value: v.pulse_bpm, unit: 'bpm' },
    { icon: Wind, label: 'Respiratory rate', value: v.respiratory_rate, unit: '/min' },
    { icon: Activity, label: 'Oxygen saturation', value: v.oxygen_saturation_pct, unit: '%', warn: (v.oxygen_saturation_pct ?? 100) < 95 },
    { icon: Ruler, label: 'Height', value: v.height_cm, unit: 'cm' },
    { icon: Weight, label: 'Weight', value: v.weight_kg, unit: 'kg', sub: bmi ? `BMI ${bmi}` : undefined },
  ]
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {items.map(({ icon: I, label, value, unit, warn, sub }) => (
        <div key={label} className="group rounded-2xl bg-raised/70 p-3.5 ring-1 ring-line/50 transition duration-300 hover:-translate-y-0.5 hover:bg-surface hover:shadow-lg hover:shadow-navy/5 hover:ring-navy/15">
          <div className="mb-2 flex items-center gap-1.5 text-xs text-muted"><I className="size-3.5 transition group-hover:text-brand" />{label}</div>
          <p className="font-display text-xl font-bold">
            {value ?? '—'}
            {value != null && <span className="ml-1 font-sans text-xs font-medium text-muted">{unit}</span>}
            {warn && <span className="ml-1.5 inline-block size-2 rounded-full bg-orange-500 align-middle" title="Outside typical range" />}
          </p>
          {sub && <p className="text-xs text-muted">{sub}</p>}
        </div>
      ))}
    </div>
  )
}

export function RecordBody({ record_id }: { record_id: number }) {
  const { db } = useStore()
  const { dxById, medById, providerName, termById } = useLookups()
  const vitals = db.vital_sign.filter((v) => v.record_id === record_id).sort((a, b) => b.recorded_at.localeCompare(a.recorded_at))
  const dx = db.record_diagnosis.filter((d) => d.record_id === record_id).sort((a) => (a.is_primary ? -1 : 1))
  const rx = db.prescription.filter((p) => p.record_id === record_id && p.status !== 'canceled')
  const refs = db.referral.filter((r) => r.record_id === record_id)
  const charges = db.student_charge.filter((c) => c.record_id === record_id)
  const r = db.medical_record.find((x) => x.record_id === record_id)!

  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_340px]">
      <div className="space-y-5">
        <Card className="p-6">
          <h3 className="mb-4 font-semibold">Vital signs</h3>
          <VitalsGrid v={vitals[0]} />
          {vitals[0] && <p className="mt-3 text-xs text-muted">Recorded {fmtDateTime(vitals[0].recorded_at)}</p>}
        </Card>
        <Card className="p-6">
          <h3 className="mb-4 font-semibold">Consultation notes</h3>
          <dl className="space-y-4 text-[15px]">
            {[
              ['Chief complaint', r.chief_complaint],
              ['Symptoms', r.symptoms],
              ['Examination', r.examination_notes],
              ['Treatment plan', r.treatment_plan],
            ].map(([k, v]) => (
              <div key={k} className="grid gap-1 sm:grid-cols-[150px_1fr]">
                <dt className="text-sm font-medium text-muted">{k}</dt>
                <dd className="leading-relaxed">{v || <span className="text-muted">Not recorded</span>}</dd>
              </div>
            ))}
          </dl>
        </Card>
        <Card className="p-6">
          <h3 className="mb-4 flex items-center gap-2 font-semibold"><Pill className="size-4 text-brand" /> Prescriptions</h3>
          {rx.length === 0 ? <p className="text-sm text-muted">No medicines were prescribed.</p> : rx.map((p) => (
            <div key={p.prescription_id} className="space-y-2">
              {db.prescription_item.filter((i) => i.prescription_id === p.prescription_id).map((i) => {
                const m = medById.get(i.medication_id)
                return (
                  <div key={i.item_id} className="flex gap-4 rounded-xl border border-line p-4">
                    <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-gold-100 text-[#6b5500] dark:bg-gold/15 dark:text-gold"><Pill className="size-4" /></span>
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold">{m?.generic_name} {m?.strength} <span className="font-normal text-muted">· {m?.dosage_form}</span></p>
                      <p className="text-sm text-muted">{i.dose}, {i.route.toLowerCase()}, {i.frequency.toLowerCase()} for {i.duration_days} days</p>
                      {i.instructions && <p className="mt-1 text-sm">{i.instructions}</p>}
                    </div>
                    <p className="shrink-0 text-sm font-semibold">{i.quantity} {i.quantity_unit}</p>
                  </div>
                )
              })}
              <p className="pt-1 text-xs text-muted">{p.status === 'issued' && p.issued_at ? `Issued ${fmtDateTime(p.issued_at)} by ${providerName(p.prescriber_id)}` : 'Draft prescription'}</p>
            </div>
          ))}
        </Card>
      </div>
      <div className="space-y-5">
        <Card className="p-6">
          <h3 className="mb-4 font-semibold">Diagnoses</h3>
          {dx.length === 0 ? <p className="text-sm text-muted">None recorded.</p> : (
            <ul className="space-y-3">
              {dx.map((d) => {
                const x = dxById.get(d.diagnosis_id)
                return (
                  <li key={d.record_diagnosis_id}>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-brand">{x?.code}</span>
                      {d.is_primary && <Badge tone="navy">Primary</Badge>}
                    </div>
                    <p className="mt-0.5 text-sm">{x?.description}</p>
                    {d.notes && <p className="text-xs text-muted">{d.notes}</p>}
                  </li>
                )
              })}
            </ul>
          )}
        </Card>
        <Card className="p-6">
          <h3 className="mb-4 flex items-center gap-2 font-semibold"><Send className="size-4 text-brand" /> Referrals</h3>
          {refs.length === 0 ? <p className="text-sm text-muted">No referrals.</p> : refs.map((f) => (
            <div key={f.referral_id} className="rounded-xl bg-raised p-4">
              <div className="mb-1 flex items-start justify-between gap-2"><p className="text-sm font-semibold">{f.destination}</p><Status value={f.status} /></div>
              <p className="text-sm text-muted">{f.reason}</p>
              <p className="mt-2 text-xs text-muted">{fmtDate(f.referred_at)} · {providerName(f.referred_by_provider_id)}</p>
            </div>
          ))}
        </Card>
        <Card className="p-6">
          <h3 className="mb-3 font-semibold">Billing</h3>
          {r.affiliation_at_visit !== 'student' ? (
            <p className="text-sm text-muted">Visits for faculty and staff are free of charge.</p>
          ) : charges.length === 0 ? (
            <p className="text-sm text-muted">No charge was created for this visit.</p>
          ) : charges.map((c) => (
            <div key={c.charge_id} className="flex items-center justify-between gap-3">
              <div>
                <p className="font-display text-xl font-bold">{peso(c.amount)}</p>
                <p className="text-xs text-muted">{termById.get(c.term_id)?.semester} · {termById.get(c.term_id)?.academic_year}</p>
              </div>
              <Status value={c.status} />
            </div>
          ))}
        </Card>
      </div>
    </div>
  )
}

export function RecordDetail({ record_id, backTo, backLabel }: { record_id: number; backTo: string; backLabel: string }) {
  const { db } = useStore()
  const { providerName, providerById } = useLookups()
  const { go } = useNav()
  const r = db.medical_record.find((x) => x.record_id === record_id)
  if (!r) return <Empty icon={FileHeart} title="Record not found" />
  return (
    <div>
      <PageHeader
        back={{ label: backLabel, onClick: () => go(backTo) }}
        eyebrow={<><FileHeart className="size-3.5 text-gold" />Record #{r.record_id} · {r.status === 'finalized' ? 'Finalized' : 'In progress'}</>}
        title={r.chief_complaint}
        description={<>Visit on {fmtDateTime(r.visited_at)} with {providerName(r.provider_id)} · {providerById.get(r.provider_id)?.specialization}</>}
      />
      <RecordBody record_id={record_id} />
    </div>
  )
}
