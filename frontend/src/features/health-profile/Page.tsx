import { useState } from 'react'
import { Check, Phone, Plus, ShieldAlert, Star, Trash2, Users, Cake } from 'lucide-react'
import { ActionButton, Avatar, Badge, Button, Card, Field, Input, Modal, PageHeader, SectionTitle, Select, Status, Textarea, cx } from '../../components/ui'
import { age, fmtDate } from '../../data/format'
import { useStore } from '../../data/store'
import type { Affiliation } from '../../data/types'
import { useNav } from '../../nav'

export function HealthProfile({ patientId }: { patientId?: number }) {
  const { db, me, actions } = useStore()
  const { run } = useNav()
  const pid = patientId ?? me!.user_id
  const p = db.patient.find((x) => x.patient_id === pid)!
  const allergies = db.patient_allergy.filter((a) => a.patient_id === pid)
  const contacts = db.emergency_contact.filter((c) => c.patient_id === pid)
  const [info, setInfo] = useState({ date_of_birth: p.date_of_birth ?? '', department_id: String(p.department_id ?? ''), affiliation: p.affiliation ?? '', medical_history_summary: p.medical_history_summary ?? '' })
  const [contactOpen, setContactOpen] = useState(false)
  const [ct, setCt] = useState({ full_name: '', relationship: '', phone_number: '', is_primary: false })

  return (
    <div>
      {!patientId && <PageHeader title="Health profile" description="Keeping this current helps clinic staff care for you safely, especially in an emergency."
        stats={[{ icon: Cake, label: 'Age', value: age(p.date_of_birth) ?? 0, hint: p.date_of_birth ? fmtDate(p.date_of_birth) : 'Add your birthday' }, { icon: ShieldAlert, label: 'Allergies on file', value: allergies.length }, { icon: Users, label: 'Emergency contacts', value: contacts.length }]} />}
      <div className="grid gap-5 lg:grid-cols-[1.3fr_1fr]">
        <Card className="p-6">
          <SectionTitle title="Personal health information" />
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Date of birth"><Input type="date" disabled={!!patientId} value={info.date_of_birth} onChange={(e) => setInfo({ ...info, date_of_birth: e.target.value })} /></Field>
            <Field label="Affiliation" hint="Changes are re-verified by the clinic">
              <Select disabled value={info.affiliation} onChange={(e) => setInfo({ ...info, affiliation: e.target.value as Affiliation })}>
                <option value="">Awaiting review</option><option value="student">Student</option><option value="faculty">Faculty</option><option value="staff">Staff</option>
              </Select>
            </Field>
            <Field label="Department" className="sm:col-span-2">
              <Select disabled value={info.department_id} onChange={(e) => setInfo({ ...info, department_id: e.target.value })}>
                <option value="">Not set</option>
                {db.department.map((d) => <option key={d.department_id} value={d.department_id}>{d.name}</option>)}
              </Select>
            </Field>
            <Field label="Medical history" className="sm:col-span-2" hint="Conditions, surgeries, maintenance medicines">
              <Textarea readOnly rows={4} value={info.medical_history_summary} onChange={(e) => setInfo({ ...info, medical_history_summary: e.target.value })} />
            </Field>
          </div>
          <div className="mt-5 flex justify-end">
            {!patientId && <Button icon={Check} onClick={() => run(() => actions.updateBirthDate(info.date_of_birth || null), 'Health information saved.')}>Save birth date</Button>}
          </div>
        </Card>

        <div className="space-y-5">
          <Card className="p-6">
            <SectionTitle title="Allergies" />
            {allergies.length === 0 ? <p className="text-sm text-muted">No allergies documented.</p> : (
              <ul className="space-y-2">
                {allergies.map((a) => (
                  <li key={a.allergy_id} className="group flex items-start gap-3 rounded-xl bg-raised p-3.5">
                    <ShieldAlert className={cx('mt-0.5 size-4 shrink-0', a.severity === 'severe' ? 'text-red-500' : a.severity === 'moderate' ? 'text-orange-500' : 'text-gold-600')} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2"><p className="font-semibold">{a.allergen}</p><Status value={a.severity} /></div>
                      {a.reaction && <p className="text-sm text-muted">{a.reaction}</p>}
                    </div>

                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card className="p-6">
            <SectionTitle title="Emergency contacts" action={!patientId && <Button size="sm" variant="outline" icon={Plus} onClick={() => setContactOpen(true)}>Add</Button>} />
            {contacts.length === 0 ? <p className="text-sm text-muted">Add someone we can reach if you need help.</p> : (
              <ul className="space-y-2">
                {contacts.map((c) => (
                  <li key={c.contact_id} className="group flex items-center gap-3 rounded-xl bg-raised p-3.5">
                    <Avatar name={c.full_name} size="sm" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2"><p className="font-semibold">{c.full_name}</p>{c.is_primary && <Badge tone="navy">Primary</Badge>}</div>
                      <p className="flex items-center gap-1.5 text-sm text-muted">{c.relationship} · <Phone className="size-3" />{c.phone_number}</p>
                    </div>
                    {!c.is_primary && <ActionButton aria-label="Make primary" title="Make primary" onClick={() => run(() => actions.setPrimaryContact(c.contact_id))} className="cursor-pointer rounded-lg p-1.5 text-muted opacity-0 transition group-hover:opacity-100 hover:bg-surface hover:text-brand focus:opacity-100"><Star className="size-4" /></ActionButton>}
                    <ActionButton aria-label={`Remove ${c.full_name}`} onClick={() => run(() => actions.removeContact(c.contact_id))} className="cursor-pointer rounded-lg p-1.5 text-muted opacity-0 transition group-hover:opacity-100 hover:bg-surface hover:text-red-600 focus:opacity-100"><Trash2 className="size-4" /></ActionButton>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>

      <Modal open={contactOpen} onClose={() => setContactOpen(false)} title="Add emergency contact">
        <div className="grid grid-cols-2 gap-4">
          <Field label="Full name" className="col-span-2"><Input value={ct.full_name} onChange={(e) => setCt({ ...ct, full_name: e.target.value })} /></Field>
          <Field label="Relationship"><Input value={ct.relationship} onChange={(e) => setCt({ ...ct, relationship: e.target.value })} placeholder="Mother" /></Field>
          <Field label="Phone"><Input value={ct.phone_number} onChange={(e) => setCt({ ...ct, phone_number: e.target.value })} placeholder="+63 9xx xxx xxxx" /></Field>
          <label className="col-span-2 flex cursor-pointer items-center gap-2 text-sm"><input type="checkbox" className="size-4 accent-[#002870]" checked={ct.is_primary} onChange={(e) => setCt({ ...ct, is_primary: e.target.checked })} /> Make this my primary contact</label>
          <Button className="col-span-2" onClick={async () => { if (await run(() => actions.addContact( { ...ct, relationship: ct.relationship || 'Other' }), 'Contact added.')) { setContactOpen(false); setCt({ full_name: '', relationship: '', phone_number: '', is_primary: false }) } }}>Save contact</Button>
        </div>
      </Modal>
    </div>
  )
}
