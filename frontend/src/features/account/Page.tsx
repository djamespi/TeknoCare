import { useState } from 'react'
import { Check } from 'lucide-react'
import { Avatar, Button, Card, Field, Input, PageHeader, SectionTitle, Textarea, Toggle } from '../../components/ui'
import { fmtDate } from '../../data/format'
import { useLookups, useStore } from '../../data/store'
import { useNav } from '../../nav'

export default function Account() {
  const { db, me, actions } = useStore()
  const { run } = useNav()
  const { name } = useLookups()
  const u = me!
  const profile = db.user_profile.find((p) => p.user_id === u.user_id)
  const settings = db.user_settings.find((s) => s.user_id === u.user_id)!
  const [f, setF] = useState({ fname: u.fname, lname: u.lname, email: u.email, phone_number: profile?.phone_number ?? '', home_address: profile?.home_address ?? '', bio: profile?.bio ?? '' })
  return (
    <div>
      <PageHeader title="Account & settings" description="Manage your personal details and how TeknoCare works for you." eyebrow={<>{u.school_id} · Member since {fmtDate(u.created_at, { month: 'long', year: 'numeric' })}</>} />
      <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        <Card className="p-6">
          <div className="mb-6 flex items-center gap-4">
            <Avatar name={name(u.user_id)} size="lg" />
            <div><p className="font-display text-xl font-bold">{name(u.user_id)}</p><p className="text-sm text-muted">{u.school_id} · Member since {fmtDate(u.created_at, { month: 'long', year: 'numeric' })}</p></div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="First name"><Input readOnly value={f.fname} /></Field>
            <Field label="Last name"><Input readOnly value={f.lname} /></Field>
            <Field label="Email" className="sm:col-span-2"><Input type="email" readOnly value={f.email} /></Field>
            <Field label="Phone number"><Input value={f.phone_number} onChange={(e) => setF({ ...f, phone_number: e.target.value })} /></Field>
            <Field label="Home address"><Input value={f.home_address} onChange={(e) => setF({ ...f, home_address: e.target.value })} /></Field>
            <Field label="About you" className="sm:col-span-2"><Textarea value={f.bio} onChange={(e) => setF({ ...f, bio: e.target.value })} /></Field>
          </div>
          <div className="mt-5 flex justify-end">
            <Button icon={Check} onClick={() => run(() => actions.updateProfile({ phone_number: f.phone_number, home_address: f.home_address, bio: f.bio }), 'Profile saved.')}>Save profile</Button>
          </div>
        </Card>
        <div className="space-y-5">
          <Card className="p-6">
            <SectionTitle title="Preferences" />
            <div className="divide-y divide-line">
              <Toggle label="Dark mode" description="Easier on the eyes at night" checked={settings.dark_mode} onChange={(v) => run(() => actions.updateSettings(u.user_id, { dark_mode: v }))} />
              <Toggle label="Email notifications" description="Saves a preference. Email delivery is unavailable." checked={settings.email_notifications} onChange={(v) => run(() => actions.updateSettings(u.user_id, { email_notifications: v }))} />
            </div>
          </Card>
          <Card className="p-6">
            <SectionTitle title="Account security" />
            <a className="font-semibold text-brand underline" href="/login/password/">Change password</a>
            {u.user_type !== 'patient' && db.patient.some(patient => patient.patient_id === u.user_id) && <div className="mt-4 space-y-2">
              <a className="block font-semibold text-brand underline" href="/appointments/">My appointments</a>
              <a className="block font-semibold text-brand underline" href="/patients/visits/">My visit summaries</a>
              <a className="block font-semibold text-brand underline" href="/patients/">My patient details</a>
            </div>}
          </Card>
        </div>
      </div>
    </div>
  )
}
