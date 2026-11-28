import { Activity, Gauge, HeartPulse, Ruler, Thermometer, Weight, Wind } from 'lucide-react'
import type { VitalSign } from '../../data/types'

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
