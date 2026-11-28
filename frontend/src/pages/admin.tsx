import { useState } from 'react'
import { Ban, BookMarked, Building2, CalendarDays, Check, CircleCheck, DoorOpen, GraduationCap, Pill, ShieldAlert, Plus, Receipt, ScrollText, Search, Send, UserCheck, Users, Wallet } from 'lucide-react'
import { Avatar, Badge, Button, Card, Empty, Field, Input, Modal, PageHeader, SectionTitle, Select, Stat, Status, Tabs, Toggle, cx } from '../components/ui'
import { dayKey, displayChargeReference, fmtDate, fmtDateTime, peso, relative } from '../data/format'
import { DomainError, useLookups, useStore } from '../data/store'
import type { AccountStatus, DB } from '../data/types'
import { useNav } from '../nav'

export function Overview() {
  const { db, actions, demo, openReferrals } = useStore()
  const { go, run } = useNav()
  const { name, slotById } = useLookups()
  const weekAhead = Date.now() + 7 * 86_400_000
  const upcoming = db.appointment.filter((a) => a.status === 'booked' && Date.parse(slotById.get(a.slot_id)!.start_time) >= Date.now() && Date.parse(slotById.get(a.slot_id)!.start_time) < weekAhead).length
  const review = demo ? db.user.filter(user => user.account_status === "suspended" && user.user_type !== "admin") : []
  const pendingCharges = db.student_charge.filter((c) => c.status === 'pending')
  const openTerm = db.academic_term.find((t) => t.is_open_for_charges)
  return (
    <div>
      <PageHeader
        eyebrow={<><span className="size-1.5 rounded-full bg-gold" />{openTerm ? `${openTerm.semester}, ${openTerm.academic_year} is open for charges` : 'No term is open for charges'}</>}
        title={<>Clinic <span className="text-shine">overview</span></>}
        description="A live view of patients, visits and billing at the Health Services Center."
        action={<Button variant="glass" icon={UserCheck} onClick={() => go('users')}>Manage accounts</Button>}
        stats={[
          { icon: Users, label: 'Registered patients', value: db.patient.length },
          { icon: CalendarDays, label: 'Visits in the next 7 days', value: upcoming },
          { icon: Send, label: 'Open referrals', value: openReferrals },
          { icon: Wallet, label: 'Charges awaiting posting', value: pendingCharges.reduce((s, c) => s + c.amount, 0), format: peso },
        ]}
      />
      <div className="mb-5 grid gap-5 lg:grid-cols-[1.7fr_1fr]">
        <VisitsChart />
        <AffiliationDonut />
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        <Card className="p-6">
          {demo && <div className="mb-5">
            <SectionTitle title="Suspended accounts" description="Review access before reactivating an account." action={review.length > 0 && <Badge tone="gold">{review.length} suspended</Badge>} />
            {review.length === 0 ? <Empty icon={UserCheck} title="All caught up" /> : <ul className="divide-y divide-line">
              {review.map(u => <li key={u.user_id} className="flex items-center gap-3 py-3">
                <Avatar name={name(u.user_id)} /><div className="flex-1"><p className="font-semibold">{name(u.user_id)}</p><p className="text-xs text-muted">{u.school_id}</p></div>
                <Button size="sm" icon={Check} onClick={() => run(() => actions.setAccountStatus(u.user_id, 'active'), 'Account reactivated.')}>Reactivate</Button>
              </li>)}
            </ul>}
          </div>}
          <SectionTitle title="Reception" description="Manage arrivals and open encounters for checked-in patients." />
          <a className="font-semibold text-brand underline" href="/reception/">Open reception queue</a>
        </Card>
        <Card className="p-6">
          <SectionTitle title="Recent activity" action={<Button size="sm" variant="ghost" onClick={() => go('audit')}>Full log</Button>} />
          <ul className="space-y-4">
            {db.audit_log.slice(0, 6).map((l) => (
              <li key={l.log_id} className="flex gap-3">
                <span className="mt-1.5 size-2 shrink-0 rounded-full bg-gold" />
                <div className="min-w-0 flex-1"><p className="text-sm"><span className="font-semibold">{name(l.actor_user_id)}</span> <span className="text-muted">{l.action_performed.toLowerCase()}</span></p><p className="text-xs text-muted">{relative(l.logged_at)} · {l.target_table} #{l.target_record_id}</p></div>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  )
}

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


function VisitsChart() {
  const { db } = useStore()
  const { slotById } = useLookups()
  const days: Date[] = []
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  d.setDate(d.getDate() - 16)
  while (days.length < 15) {
    if (d.getDay() !== 0 && d.getDay() !== 6) days.push(new Date(d))
    d.setDate(d.getDate() + 1)
  }
  const today = dayKey(new Date().toISOString())
  const counts = days.map((day) => {
    const k = dayKey(day.toISOString())
    const list = db.appointment.filter((a) => a.status !== 'canceled' && dayKey(slotById.get(a.slot_id)!.start_time) === k)
    return { day, k, total: list.length, done: list.filter((a) => a.status === 'completed').length }
  })
  const max = Math.max(4, ...counts.map((c) => c.total))
  return (
    <Card className="p-6">
      <SectionTitle title="Visits" description="Booked appointments by day across the last three weeks" action={<div className="flex gap-3 text-xs text-muted"><span className="flex items-center gap-1.5"><span className="size-2.5 rounded-sm bg-navy dark:bg-navy-100" />Completed</span><span className="flex items-center gap-1.5"><span className="size-2.5 rounded-sm bg-navy-100 dark:bg-navy-700" />Booked</span></div>} />
      <div className="relative mt-2 flex h-48 items-end gap-1.5 sm:gap-2.5">
        {[0.25, 0.5, 0.75, 1].map((f) => <div key={f} className="pointer-events-none absolute inset-x-0 border-t border-dashed border-line" style={{ bottom: `${f * 100}%` }} />)}
        {counts.map((c, i) => (
          <div key={c.k} className="group relative flex h-full flex-1 flex-col justify-end">
            <div className="pointer-events-none absolute -top-2 left-1/2 z-10 -translate-x-1/2 -translate-y-full rounded-lg bg-navy-950 px-2.5 py-1.5 text-center text-[11px] whitespace-nowrap text-white opacity-0 shadow-xl transition group-hover:opacity-100">
              <span className="font-semibold">{c.total}</span> visits · {c.day.toLocaleDateString('en-PH', { month: 'short', day: 'numeric' })}
            </div>
            <div className="grow-y relative w-full overflow-hidden rounded-t-lg transition group-hover:brightness-110" style={{ height: `${(c.total / max) * 100}%`, minHeight: 4, animationDelay: `${i * 45}ms` }}>
              <div className={cx('absolute inset-0', c.k === today ? 'bg-gradient-to-t from-gold-600 to-gold' : 'bg-navy-100 dark:bg-navy-700')} />
              {c.k !== today && <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-navy to-navy-700 dark:from-navy-100 dark:to-navy-100" style={{ height: c.total ? `${(c.done / c.total) * 100}%` : 0 }} />}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-2 flex gap-1.5 sm:gap-2.5">
        {counts.map((c) => <span key={c.k} className={cx('flex-1 text-center text-[10px] sm:text-[11px]', c.k === today ? 'font-bold text-ink' : 'text-muted')}>{c.k === today ? 'Today' : c.day.getDate()}</span>)}
      </div>
    </Card>
  )
}

function AffiliationDonut() {
  const { db } = useStore()
  const groups = [
    { label: 'Students', value: db.patient.filter((p) => p.affiliation === 'student').length, color: '#002870' },
    { label: 'Faculty', value: db.patient.filter((p) => p.affiliation === 'faculty').length, color: '#fdd108' },
    { label: 'Staff', value: db.patient.filter((p) => p.affiliation === 'staff').length, color: '#7f9bd6' },
  ]
  const total = groups.reduce((s, g) => s + g.value, 0) || 1
  const r = 52
  const C = 2 * Math.PI * r
  let acc = 0
  return (
    <Card className="p-6">
      <SectionTitle title="Who we serve" description="Registered patients by affiliation" />
      <div className="flex items-center gap-6">
        <div className="relative size-36 shrink-0">
          <svg viewBox="0 0 128 128" className="size-full -rotate-90">
            <circle cx="64" cy="64" r={r} fill="none" stroke="var(--tc-raised)" strokeWidth="16" />
            {groups.map((g, i) => {
              const len = (g.value / total) * C
              const el = (
                <circle key={g.label} cx="64" cy="64" r={r} fill="none" stroke={g.color} strokeWidth="16" strokeLinecap="butt"
                  strokeDasharray={`${len} ${C - len}`} strokeDashoffset={-acc}
                  className="donut-segment origin-center transition-all duration-700" style={{ animationDelay: `${i * 120}ms` }} />
              )
              acc += len
              return el
            })}
          </svg>
          <div className="absolute inset-0 grid place-items-center text-center">
            <div><p className="font-display text-3xl leading-none font-bold">{total}</p><p className="text-xs text-muted">patients</p></div>
          </div>
        </div>
        <ul className="flex-1 space-y-3">
          {groups.map((g) => (
            <li key={g.label}>
              <div className="flex items-center justify-between text-sm"><span className="flex items-center gap-2"><span className="size-2.5 rounded-full" style={{ background: g.color }} />{g.label}</span><span className="font-semibold">{g.value}</span></div>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-raised"><div className="h-full rounded-full transition-all duration-1000" style={{ width: `${(g.value / total) * 100}%`, background: g.color }} /></div>
            </li>
          ))}
        </ul>
      </div>
    </Card>
  )
}
