import { useState } from 'react'
import { CalendarDays, ScrollText, Users } from 'lucide-react'
import { Card, Empty, PageHeader, Select } from '../../components/ui'
import { dayKey, fmtDateTime } from '../../data/format'
import { useLookups, useStore } from '../../data/store'

export function Audit() {
  const { db } = useStore()
  const { name } = useLookups()
  const [table, setTable] = useState('all')
  const tables = [...new Set(db.audit_log.map((l) => l.target_table))].sort()
  const rows = db.audit_log.filter((l) => table === 'all' || l.target_table === table)
  return (
    <div>
      <PageHeader title="Audit log" description="Every change to patient and clinic data, with who made it and when."
        stats={[{ icon: ScrollText, label: 'Events recorded', value: db.audit_log.length }, { icon: Users, label: 'People active', value: new Set(db.audit_log.map((l) => l.actor_user_id).filter(Boolean)).size }, { icon: CalendarDays, label: 'Today', value: db.audit_log.filter((l) => dayKey(l.logged_at) === dayKey(new Date().toISOString())).length }]} />
      <div className="mb-5"><Select className="sm:w-64" value={table} onChange={(e) => setTable(e.target.value)}><option value="all">All tables</option>{tables.map((t) => <option key={t}>{t}</option>)}</Select></div>
      <Card className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <thead className="border-b border-line bg-raised/60 text-left text-[13px] text-muted"><tr><th className="px-5 py-3 font-semibold">When</th><th className="px-5 py-3 font-semibold">Who</th><th className="px-5 py-3 font-semibold">Action</th><th className="px-5 py-3 font-semibold">Target</th></tr></thead>
          <tbody className="divide-y divide-line">
            {rows.map((l) => (
              <tr key={l.log_id} className="hover:bg-raised/40">
                <td className="px-5 py-3 whitespace-nowrap text-muted">{fmtDateTime(l.logged_at)}</td>
                <td className="px-5 py-3 font-semibold">{name(l.actor_user_id)}</td>
                <td className="px-5 py-3">{l.action_performed}</td>
                <td className="px-5 py-3"><span className="rounded-md bg-raised px-2 py-1 font-mono text-xs">{l.target_table} #{l.target_record_id}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <Empty icon={ScrollText} title="No activity" />}
      </Card>
    </div>
  )
}
