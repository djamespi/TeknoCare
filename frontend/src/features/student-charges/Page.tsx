import { useState } from 'react'
import { Ban, CircleCheck, Receipt } from 'lucide-react'
import { Button, Card, Empty, Field, Input, Modal, PageHeader, Select, Status, Tabs, cx } from '../../components/ui'
import { displayChargeReference, fmtDate, peso } from '../../data/format'
import { useLookups, useStore } from '../../data/store'
import { useNav } from '../../nav'

export function Charges() {
  const { db, actions } = useStore()
  const { run } = useNav()
  const { name, termById, recordById } = useLookups()
  const [status, setStatus] = useState<'all' | 'pending' | 'posted' | 'voided'>('pending')
  const [confirmation, setConfirmation] = useState<{ id: number; operation: 'post' | 'void'; status: string } | null>(null)
  const [reason, setReason] = useState('')
  const [term, setTerm] = useState('all')
  const rows = db.student_charge.filter((c) => (status === 'all' || c.status === status) && (term === 'all' || c.term_id === Number(term))).sort((a, b) => b.created_at.localeCompare(a.created_at))
  const count = (s: string) => db.student_charge.filter((c) => c.status === s).length
  return (
    <div>
      <PageHeader title="Student charges" description="Review student visit charges and their tuition posting status. Posting records a simulated tuition charge. Payment is handled outside TeknoCare." action={<Button variant="accent" data-page-load onClick={() => window.location.assign('/clinic/charges/find/')}>Find an encounter</Button>}
        stats={[
          { icon: Receipt, label: 'Pending', value: db.student_charge.filter((c) => c.status === 'pending').reduce((s, c) => s + c.amount, 0), format: peso, hint: `${count('pending')} charges` },
          { icon: CircleCheck, label: 'Posted to tuition', value: db.student_charge.filter((c) => c.status === 'posted').reduce((s, c) => s + c.amount, 0), format: peso, hint: `${count('posted')} charges` },
          { icon: Ban, label: 'Voided', value: count('voided'), hint: 'Reversed or canceled' },
        ]} />
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:justify-between">
        <Tabs value={status} onChange={setStatus} items={[{ value: 'pending', label: 'Pending', count: count('pending') }, { value: 'posted', label: 'Posted', count: count('posted') }, { value: 'voided', label: 'Voided', count: count('voided') }, { value: 'all', label: 'All' }]} />
        <Select className="sm:w-64" value={term} onChange={(e) => setTerm(e.target.value)}>
          <option value="all">All terms</option>
          {db.academic_term.map((t) => <option key={t.term_id} value={t.term_id}>{t.semester}, {t.academic_year}</option>)}
        </Select>
      </div>
      <Card className="overflow-x-auto">
        <table className="w-full min-w-[820px] text-sm">
          <thead className="border-b border-line bg-raised/60 text-left text-[13px] text-muted"><tr><th className="px-5 py-3 font-semibold">Charge</th><th className="px-5 py-3 font-semibold">Student</th><th className="px-5 py-3 font-semibold">Term</th><th className="px-5 py-3 font-semibold">Status</th><th className="px-5 py-3 text-right font-semibold">Amount</th><th className="px-5 py-3" /></tr></thead>
          <tbody className="divide-y divide-line">
            {rows.map((c) => {
              const t = termById.get(c.term_id)
              return (
                <tr key={c.charge_id} className="hover:bg-raised/40">
                  <td className="px-5 py-4"><p className="font-mono text-xs font-semibold">{c.charge_code}</p><p className="text-xs text-muted">{displayChargeReference(c.billing_reference ?? c.reversal_reference) ?? fmtDate(c.created_at)}</p></td>
                  <td className="px-5 py-4"><p className="font-semibold">{name(c.patient_id)}</p><p className="text-xs text-muted">Encounter #{c.record_id}</p></td>
                  <td className="px-5 py-4 text-muted">{t?.semester}, {t?.academic_year}</td>
                  <td className="px-5 py-4"><Status value={c.status} />{c.void_reason && <p className="mt-1 max-w-48 text-xs text-muted">{c.void_reason}</p>}</td>
                  <td className={cx('px-5 py-4 text-right font-semibold', c.status === 'voided' && 'text-muted line-through')}>{peso(c.amount)}</td>
                  <td className="px-5 py-4 text-right">
                    <div className="flex justify-end gap-1">
                      {c.status === 'pending' && <Button size="sm" icon={Receipt} onClick={() => setConfirmation({ id: c.charge_id, operation: 'post', status: c.status })}>Post</Button>}
                      {(c.status === 'pending' || c.billing_reference === `DEMO-POST-${c.charge_code}` && c.status === 'posted') && <Button size="sm" variant="danger" icon={Ban} onClick={() => { setReason(''); setConfirmation({ id: c.charge_id, operation: 'void', status: c.status }) }}>Void</Button>}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {rows.length === 0 && <Empty icon={Receipt} title="No charges here" />}
      </Card>

      <Modal open={confirmation !== null} onClose={() => setConfirmation(null)}
        title={confirmation?.operation === 'post' ? 'Post this charge?' : 'Void this charge?'}
        description="Confirm the simulated tuition action.">
        {confirmation?.operation === 'void' && <Field label="Reason"><Input value={reason} onChange={e => setReason(e.target.value)} /></Field>}
        <div className="mt-6 flex justify-end gap-2"><Button variant="ghost" onClick={() => setConfirmation(null)}>Keep charge</Button>
          <Button disabled={confirmation?.operation === 'void' && !reason.trim()} onClick={async () => {
            if (confirmation && await run(() => actions.changeCharge(confirmation.id, confirmation.operation, confirmation.status, reason), 'Charge updated.')) setConfirmation(null)
          }}>{confirmation?.operation === 'post' ? 'Simulate posting' : 'Void charge'}</Button></div>
      </Modal>
    </div>
  )
}
