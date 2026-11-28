import { useState } from 'react'
import {
AlertOctagon,CalendarPlus,FileHeart,Users
} from 'lucide-react'
import { Avatar, Card, Empty, PageHeader, Status, Tabs } from '../../components/ui'
import { fmtDate, fmtTime } from '../../data/format'
import { useLookups, useStore } from '../../data/store'
import { useNav } from '../../nav'
import { HealthProfile } from '../health-profile/Page'

export function PatientFile({ patientId }: { patientId: number }) {
  const { db } = useStore()
  const { go } = useNav()
  const { name, providerName, slotById } = useLookups()
  const [tab, setTab] = useState<'visits' | 'profile' | 'appointments'>('visits')
  const u = db.user.find((x) => x.user_id === patientId)
  if (!u) return <Empty icon={Users} title="Patient not found" />
  const records = db.medical_record.filter((r) => r.patient_id === patientId).sort((a, b) => b.visited_at.localeCompare(a.visited_at))
  const appts = db.appointment.filter((a) => a.patient_id === patientId).map((a) => ({ ...a, slot: slotById.get(a.slot_id)! })).sort((a, b) => b.slot.start_time.localeCompare(a.slot.start_time))
  const profile = db.user_profile.find((x) => x.user_id === patientId)
  return (
    <div>
      <PageHeader
        back={{ label: 'All patients', onClick: () => go('patients') }}
        eyebrow={<>{u.school_id} · {u.email}{profile?.phone_number && ` · ${profile.phone_number}`}</>}
        title={<span className="flex items-center gap-4"><Avatar name={name(patientId)} tone="gold" size="lg" className="hidden sm:grid" />{name(patientId)}</span>}
        stats={[{ icon: FileHeart, label: 'Visits', value: records.length }, { icon: CalendarPlus, label: 'Appointments', value: appts.length }, { icon: AlertOctagon, label: 'Allergies', value: db.patient_allergy.filter((a) => a.patient_id === patientId).length }]}
      />
      <div className="mb-5"><Tabs value={tab} onChange={setTab} items={[{ value: 'visits', label: 'Visits', count: records.length }, { value: 'appointments', label: 'Appointments', count: appts.length }, { value: 'profile', label: 'Health profile' }]} /></div>
      {tab === 'visits' && (
        <Card className="divide-y divide-line">
          {records.length === 0 && <Empty icon={FileHeart} title="No visits yet" />}
          {records.map((r) => (
            <button key={r.record_id} onClick={() => go(r.status === 'draft' ? `encounter/${r.record_id}` : `patients/${patientId}/record/${r.record_id}`)} className="flex w-full cursor-pointer items-center gap-4 p-5 text-left hover:bg-raised/60">
              <div className="w-24 shrink-0 text-sm"><p className="font-semibold">{fmtDate(r.visited_at, { month: 'short', day: 'numeric' })}</p><p className="text-xs text-muted">{new Date(r.visited_at).getFullYear()}</p></div>
              <div className="min-w-0 flex-1"><p className="font-semibold">{r.chief_complaint}</p><p className="truncate text-sm text-muted">{providerName(r.provider_id)} · {r.treatment_plan ?? 'No plan yet'}</p></div>
              <Status value={r.status} />
            </button>
          ))}
        </Card>
      )}
      {tab === 'appointments' && (
        <Card className="divide-y divide-line">
          {appts.map((a) => (
            <div key={a.appointment_id} className="flex items-center gap-4 p-5">
              <div className="w-40 shrink-0 text-sm"><p className="font-semibold">{fmtDate(a.slot.start_time)}</p><p className="text-xs text-muted">{fmtTime(a.slot.start_time)}</p></div>
              <div className="min-w-0 flex-1"><p className="text-sm">{a.reason_for_visit}</p><p className="text-xs text-muted">{providerName(a.slot.provider_id)}</p></div>
              <Status value={a.status} />
            </div>
          ))}
        </Card>
      )}
      {tab === 'profile' && <HealthProfile patientId={patientId} />}
    </div>
  )
}
