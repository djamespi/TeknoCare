import { FileHeart, Pill, Send } from 'lucide-react'
import { Badge, Card, Empty, PageHeader, Reveal } from '../../components/ui'
import { fmtDate } from '../../data/format'
import { useStore } from '../../data/store'
import { useNav } from '../../nav'
import { usePatientData } from '../../data/usePatientData'

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
