import { useState } from 'react'
import { BookMarked, Building2, CalendarDays, DoorOpen, GraduationCap, Pill, Plus } from 'lucide-react'
import { Button, Card, Field, Input, Modal, PageHeader, Tabs, Toggle } from '../../components/ui'
import { fmtDate } from '../../data/format'
import { DomainError, useStore } from '../../data/store'
import type { DB } from '../../data/types'
import { useNav } from '../../nav'

type CatalogTab = 'department' | 'clinic_room' | 'academic_term' | 'diagnosis' | 'medication'

export function Catalog() {
  const { db, actions } = useStore()
  const { run } = useNav()
  const [tab, setTab] = useState<CatalogTab>('clinic_room')
  const [open, setOpen] = useState(false)
  const [f, setF] = useState<Record<string, string>>({})
  const set = (k: string) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value })

  const config: Record<CatalogTab, { label: string; icon: typeof Building2; fields: [string, string, string?][]; pk: string; rows: Record<string, unknown>[]; cols: [string, (r: never) => React.ReactNode][]; toggle?: string; unique?: (d: DB) => boolean; build: (id: number) => object }> = {
    clinic_room: {
      label: 'room', icon: DoorOpen, pk: 'room_id', rows: db.clinic_room as never, toggle: 'is_active',
      fields: [['campus', 'Campus', 'Main Campus'], ['building', 'Building', 'Health Services Center'], ['room_number', 'Room number', 'HSC-103']],
      cols: [['Room', (r: DB['clinic_room'][number]) => <span className="font-semibold">{r.room_number}</span>], ['Building', (r: DB['clinic_room'][number]) => r.building], ['Campus', (r: DB['clinic_room'][number]) => r.campus]] as never,
      unique: (d) => d.clinic_room.some((r) => r.campus === f.campus && r.building === f.building && r.room_number === f.room_number),
      build: (id) => ({ room_id: id, campus: f.campus ?? '', building: f.building ?? '', room_number: f.room_number ?? '', is_active: true }),
    },
    department: {
      label: 'department', icon: Building2, pk: 'department_id', rows: db.department as never, toggle: 'is_active',
      fields: [['code', 'Code', 'CCS'], ['name', 'Name', 'College of Computer Studies']],
      cols: [['Code', (r: DB['department'][number]) => <span className="font-mono text-xs font-semibold">{r.code}</span>], ['Name', (r: DB['department'][number]) => r.name]] as never,
      unique: (d) => d.department.some((x) => x.code.toLowerCase() === (f.code ?? '').toLowerCase()),
      build: (id) => ({ department_id: id, code: f.code ?? '', name: f.name ?? '', is_active: true }),
    },
    academic_term: {
      label: 'academic term', icon: CalendarDays, pk: 'term_id', rows: db.academic_term as never, toggle: 'is_open_for_charges',
      fields: [['academic_year', 'Academic year', '2026-2027'], ['semester', 'Semester', '1st Semester'], ['start_date', 'Start date', 'date'], ['end_date', 'End date', 'date']],
      cols: [['Term', (r: DB['academic_term'][number]) => <span className="font-semibold">{r.semester}, {r.academic_year}</span>], ['Dates', (r: DB['academic_term'][number]) => `${fmtDate(r.start_date)} – ${fmtDate(r.end_date)}`]] as never,
      unique: (d) => d.academic_term.some((t) => t.academic_year === f.academic_year && t.semester === f.semester),
      build: (id) => ({ term_id: id, academic_year: f.academic_year ?? '', semester: f.semester ?? '', start_date: f.start_date ?? '', end_date: f.end_date ?? '', is_open_for_charges: false }),
    },
    diagnosis: {
      label: 'diagnosis code', icon: BookMarked, pk: 'diagnosis_id', rows: db.diagnosis as never,
      fields: [['code', 'Code', 'J20.9'], ['description', 'Description', 'Acute bronchitis, unspecified'], ['coding_system', 'Coding system', 'ICD-10-CM']],
      cols: [['Code', (r: DB['diagnosis'][number]) => <span className="font-mono text-xs font-semibold text-brand">{r.code}</span>], ['Description', (r: DB['diagnosis'][number]) => r.description], ['System', (r: DB['diagnosis'][number]) => r.coding_system]] as never,
      unique: (d) => d.diagnosis.some((x) => x.code === f.code && x.coding_system === (f.coding_system || 'ICD-10-CM')),
      build: (id) => ({ diagnosis_id: id, code: f.code ?? '', description: f.description ?? '', coding_system: f.coding_system || 'ICD-10-CM' }),
    },
    medication: {
      label: 'medicine', icon: Pill, pk: 'medication_id', rows: db.medication as never, toggle: 'is_active',
      fields: [['medication_code', 'Code', 'PAR-250S'], ['generic_name', 'Generic name', 'Paracetamol'], ['strength', 'Strength', '250 mg/5 mL'], ['dosage_form', 'Dosage form', 'Syrup']],
      cols: [['Medicine', (r: DB['medication'][number]) => <span className="font-semibold">{r.generic_name}</span>], ['Strength', (r: DB['medication'][number]) => `${r.strength} · ${r.dosage_form}`], ['Code', (r: DB['medication'][number]) => <span className="font-mono text-xs">{r.medication_code}</span>]] as never,
      unique: (d) => d.medication.some((x) => x.medication_code === f.medication_code),
      build: (id) => ({ medication_id: id, medication_code: f.medication_code ?? '', generic_name: f.generic_name ?? '', strength: f.strength ?? '', dosage_form: f.dosage_form ?? '', is_active: true }),
    },
  }
  const c = config[tab]
  const toggleLabel = tab === 'academic_term' ? 'Open for charges' : 'Active'

  return (
    <div>
      <PageHeader title="Clinic setup" description="Reference data used across scheduling, charting and billing." action={<Button variant="accent" icon={Plus} onClick={() => { setF({}); setOpen(true) }}>Add {c.label}</Button>}
        stats={[{ icon: DoorOpen, label: 'Active rooms', value: db.clinic_room.filter((r) => r.is_active).length }, { icon: BookMarked, label: 'Diagnosis codes', value: db.diagnosis.length }, { icon: Pill, label: 'Medicines', value: db.medication.length }, { icon: GraduationCap, label: 'Academic terms', value: db.academic_term.length }]} />
      <div className="mb-5">
        <Tabs value={tab} onChange={setTab} items={[{ value: 'clinic_room', label: 'Rooms' }, { value: 'department', label: 'Departments' }, { value: 'academic_term', label: 'Terms' }, { value: 'diagnosis', label: 'Diagnoses' }, { value: 'medication', label: 'Medicines' }]} />
      </div>
      <Card className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <thead className="border-b border-line bg-raised/60 text-left text-[13px] text-muted"><tr>{c.cols.map(([h]) => <th key={h} className="px-5 py-3 font-semibold">{h}</th>)}{c.toggle && <th className="w-40 px-5 py-3 font-semibold">{toggleLabel}</th>}</tr></thead>
          <tbody className="divide-y divide-line">
            {c.rows.map((r) => (
              <tr key={String(r[c.pk])} className="hover:bg-raised/40">
                {c.cols.map(([h, render]) => <td key={h} className="px-5 py-3.5">{render(r as never)}</td>)}
                {c.toggle && (
                  <td className="px-5 py-1">
                    <Toggle label="" checked={Boolean(r[c.toggle])} onChange={(v) => {
                      const id = Number(r[c.pk])
                      const fields = { ...r, [c.toggle!]: v }
                      delete fields[c.pk]
                      return run(() => actions.saveReference(tab, fields, id), `${v ? 'Enabled' : 'Disabled'} ${c.label}`)
                    }} />
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      

      <Modal open={open} onClose={() => setOpen(false)} title={`Add ${c.label}`}>
        <div className="space-y-4">
          {c.fields.map(([k, l, ph]) => <Field key={k} label={l}><Input type={ph === 'date' ? 'date' : 'text'} placeholder={ph === 'date' ? undefined : ph} value={f[k] ?? ''} onChange={set(k)} /></Field>)}
          <Button className="w-full" disabled={c.fields.some(([k, , ph]) => !f[k] && !(k === 'coding_system' && ph))} onClick={async () => {
            if (c.unique?.(db)) return run(() => { throw new DomainError(`That ${c.label} already exists.`) })
            const entry = c.build(0) as Record<string, unknown>
            delete entry[c.pk]
            if (await run(() => actions.saveReference(tab, entry), `Added ${c.label}.`)) setOpen(false)
          }}>Save</Button>
        </div>
      </Modal>
    </div>
  )
}
