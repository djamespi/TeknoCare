import { useState } from 'react'
import { ShieldAlert, Plus, Search, UserCheck, Users } from 'lucide-react'
import { Avatar, Button, Card, Empty, Field, Input, Modal, PageHeader, Select, Tabs } from '../../components/ui'
import { fmtDate } from '../../data/format'
import { useLookups, useStore } from '../../data/store'
import type { AccountStatus } from '../../data/types'
import { useNav } from '../../nav'

export function People() {
  const { db, actions } = useStore()
  const { run } = useNav()
  const { name, providerById, patientById, deptById } = useLookups()
  const [tab, setTab] = useState<'all' | 'patient' | 'provider' | 'admin'>('all')
  const [addOpen, setAddOpen] = useState(false)
  const [creatingProvider, setCreatingProvider] = useState(false)
  const [pv, setPv] = useState({ school_id: '', first_name: '', last_name: '', email: '',
    provider_type: 'Unverified', license_number: '', specialization: '', password1: '', password2: '' })
  const providerField = (key: keyof typeof pv) => (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setPv({ ...pv, [key]: event.target.value })
  const [q, setQ] = useState('')
  const rows = db.user.filter((u) => (tab === 'all' || u.user_type === tab) && `${u.fname} ${u.lname} ${u.email} ${u.school_id}`.toLowerCase().includes(q.toLowerCase()))
  const describe = (id: number) => {
    const p = providerById.get(id)
    if (p) {
      const designation = p.provider_type[0].toUpperCase() + p.provider_type.slice(1)
      return p.license_number?.startsWith('DEMO-') ? designation : `${designation} · ${p.license_number ?? 'No license'}`
    }
    const pt = patientById.get(id)
    if (pt) return `${pt.affiliation ? pt.affiliation[0].toUpperCase() + pt.affiliation.slice(1) : 'Patient'}${pt.department_id ? ` · ${deptById.get(pt.department_id)?.code}` : ''}`
    return 'Administrator'
  }
  return (
    <div>
      <PageHeader title="People" description="Patients, providers and administrators with access to TeknoCare." action={<Button variant="accent" icon={Plus} onClick={() => setAddOpen(true)}>Add provider</Button>}
        stats={[{ icon: Users, label: 'Patients', value: db.user.filter((u) => u.user_type === 'patient').length }, { icon: ShieldAlert, label: 'Providers', value: db.provider.length }, { icon: UserCheck, label: 'Active accounts', value: db.user.filter((u) => u.account_status === 'active').length }]} />
      <div className="mb-5 flex flex-col gap-3 lg:flex-row">
        <Tabs value={tab} onChange={setTab} items={[{ value: 'all', label: 'Everyone' }, { value: 'patient', label: 'Patients' }, { value: 'provider', label: 'Providers' }, { value: 'admin', label: 'Admins' }]} />
        <div className="relative flex-1"><Search className="pointer-events-none absolute top-3.5 left-3.5 size-4 text-muted" /><Input className="pl-10" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search people" /></div>
      </div>
      <Card className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead className="border-b border-line bg-raised/60 text-left text-[13px] text-muted"><tr><th className="px-5 py-3 font-semibold">Name</th><th className="px-5 py-3 font-semibold">School ID</th><th className="px-5 py-3 font-semibold">Role</th><th className="px-5 py-3 font-semibold">Joined</th><th className="px-5 py-3 font-semibold">Status</th></tr></thead>
          <tbody className="divide-y divide-line">
            {rows.map((u) => (
              <tr key={u.user_id} className="hover:bg-raised/40">
                <td className="px-5 py-3.5"><div className="flex items-center gap-3"><Avatar name={name(u.user_id)} size="sm" /><div><p className="font-semibold">{name(u.user_id)}</p><p className="text-xs text-muted">{u.email}</p></div></div></td>
                <td className="px-5 py-3.5 font-mono text-xs">{u.school_id}</td>
                <td className="px-5 py-3.5 text-muted">{describe(u.user_id)}</td>
                <td className="px-5 py-3.5 text-muted">{fmtDate(u.created_at)}</td>
                <td className="px-5 py-3.5">
                  <Select disabled={u.user_type === "admin"} className="h-9 w-36 text-xs" value={u.account_status} onChange={(e) => run(() => actions.setAccountStatus(u.user_id, e.target.value as AccountStatus), 'Account updated.')}>
                    <option value="active">Active</option><option value="suspended">Suspended</option>
                  </Select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <Empty icon={Users} title="No one matches" />}
      </Card>

      <Modal open={addOpen} onClose={() => setAddOpen(false)} title="Add a provider" description="Creates an inactive provider account for clinic review." wide>
        <form className="grid grid-cols-2 gap-4" aria-busy={creatingProvider} onSubmit={async event => {
          event.preventDefault()
          if (creatingProvider) return
          setCreatingProvider(true)
          try {
            if (await run(() => actions.addProvider(pv), 'Provider account created. Review activation under Clinic setup.')) setAddOpen(false)
          } finally {
            setCreatingProvider(false)
          }
        }}>
          <Field label="First name"><Input required value={pv.first_name} onChange={providerField('first_name')} /></Field>
          <Field label="Last name"><Input required value={pv.last_name} onChange={providerField('last_name')} /></Field>
          <Field label="University ID"><Input required value={pv.school_id} onChange={providerField('school_id')} /></Field>
          <Field label="Email"><Input required type="email" value={pv.email} onChange={providerField('email')} /></Field>
          <Field label="Type"><Select value={pv.provider_type} onChange={providerField('provider_type')}>
            {['Unverified', 'Physician', 'Nurse', 'Dentist'].map(option => <option key={option}>{option}</option>)}
          </Select></Field>
          <Field label="License number"><Input value={pv.license_number} onChange={providerField('license_number')} /></Field>
          <Field label="Specialization" className="col-span-2"><Input value={pv.specialization} onChange={providerField('specialization')} /></Field>
          <Field label="Initial password"><Input required type="password" autoComplete="new-password" value={pv.password1} onChange={providerField('password1')} /></Field>
          <Field label="Confirm password"><Input required type="password" autoComplete="new-password" value={pv.password2} onChange={providerField('password2')} /></Field>
          <Button className="col-span-2" type="submit" loading={creatingProvider}>Create provider</Button>
        </form>
      </Modal>
    </div>
  )
}
