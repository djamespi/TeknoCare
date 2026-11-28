import { useState } from 'react'
import {
AlertOctagon,GraduationCap,Search,Users
} from 'lucide-react'
import { Avatar, Badge, Card, Empty, Input, PageHeader, Status, Tabs } from '../../components/ui'
import { useLookups, useStore } from '../../data/store'
import { useNav } from '../../nav'

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
