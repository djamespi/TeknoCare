import {
AlertTriangle,Clock,GraduationCap,UserRound,Wallet
} from 'lucide-react'
import { Card, Empty, PageHeader, Status, cx } from '../../components/ui'
import { displayChargeReference, fmtDate, peso } from '../../data/format'
import { useLookups, useStore } from '../../data/store'
import { useNav } from '../../nav'

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
                      <td className="px-5 py-4"><p className="font-mono text-xs font-semibold">{c.charge_code}</p><p className="text-xs text-muted">{displayChargeReference(c.billing_reference) ?? 'Not yet billed'}</p></td>
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
