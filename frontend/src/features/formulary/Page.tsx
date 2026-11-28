import { useState } from 'react'
import { CheckCircle2, Pill, Search, Library } from 'lucide-react'
import { Card, Empty, Input, PageHeader, cx } from '../../components/ui'
import { useStore } from '../../data/store'

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
