import { useMemo, useState } from 'react'
import {
AlertOctagon,CalendarPlus,CheckCircle2,ClipboardPlus,FilePen,FileHeart,Stethoscope,UserCheck,UserX,Users
} from 'lucide-react'
import { Avatar, Badge, Button, Card, Empty, PageHeader, SectionTitle, Status, cx } from '../../components/ui'
import { age, dayKey, fmtDateTime, fmtTime } from '../../data/format'
import { useLookups, useStore } from '../../data/store'
import { useNav } from '../../nav'

function weekdays(fromOffset: number, count: number) {
  const out: Date[] = []
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  d.setDate(d.getDate() + fromOffset)
  while (out.length < count) {
    if (d.getDay() !== 0 && d.getDay() !== 6) out.push(new Date(d))
    d.setDate(d.getDate() + 1)
  }
  return out
}

export function Today() {
  const { db, me, actions } = useStore()
  const { go, run } = useNav()
  const { name, slotById, patientById, deptById, roomById } = useLookups()
  const days = useMemo(() => weekdays(-2, 8), [])
  const todayKey = dayKey(new Date().toISOString())
  const [day, setDay] = useState(todayKey)
  const pid = me!.user_id
  const appts = db.appointment
    .map((a) => ({ ...a, slot: slotById.get(a.slot_id)! }))
    .filter((a) => a.slot.provider_id === pid && dayKey(a.slot.start_time) === day && a.status !== 'canceled')
    .sort((a, b) => a.slot.start_time.localeCompare(b.slot.start_time))
  const drafts = db.medical_record.filter((r) => r.status === 'draft' && (r.can_edit || r.can_record_vitals))
  const openVisit = async (appointment_id: number) => {
    let id = 0
    if (await run(async () => { id = await actions.startRecord(appointment_id) })) go(`encounter/${id}`)
  }

  return (
    <div>
      <PageHeader
        eyebrow={<><Stethoscope className="size-3.5 text-gold" />{db.provider.find((p) => p.provider_id === pid)?.specialization}</>}
        title={<>Good day, <span className="text-shine">{db.provider.find((p) => p.provider_id === pid)?.provider_type === 'nurse' ? 'Nurse' : 'Dr.'} {me!.lname}</span></>}
        description="Your patient queue. Check patients in as they arrive, then open the visit to chart."
        action={<Button variant="glass" icon={CalendarPlus} onClick={() => go('schedule')}>Manage slots</Button>}
        stats={[
          { icon: Users, label: day === todayKey ? 'Patients today' : 'Patients this day', value: appts.length },
          { icon: UserCheck, label: 'Waiting', value: appts.filter((a) => a.status === 'checked_in').length },
          { icon: CheckCircle2, label: 'Seen', value: appts.filter((a) => a.status === 'completed').length },
          { icon: FilePen, label: 'Unfinished charts', value: drafts.length },
        ]}
      >
        <div className="no-scrollbar -mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
          {days.map((d, i) => {
            const k = dayKey(d.toISOString())
            const count = db.appointment.filter((a) => a.status !== 'canceled' && slotById.get(a.slot_id)?.provider_id === pid && dayKey(slotById.get(a.slot_id)!.start_time) === k).length
            const active = k === day
            return (
              <button key={k} onClick={() => setDay(k)} style={{ animationDelay: `${300 + i * 40}ms` }}
                className={cx('animate-rise min-w-[92px] shrink-0 cursor-pointer rounded-2xl px-3.5 py-3 text-left ring-1 transition duration-300', active ? 'bg-gold text-navy-950 shadow-xl shadow-gold/20 ring-gold' : 'bg-white/[0.06] text-white ring-white/10 backdrop-blur-md hover:-translate-y-0.5 hover:bg-white/[0.1]')}>
                <span className="block text-xs font-semibold opacity-70">{k === todayKey ? 'Today' : d.toLocaleDateString('en-PH', { weekday: 'short' })}</span>
                <span className="block font-display text-lg font-bold">{d.toLocaleDateString('en-PH', { month: 'short', day: 'numeric' })}</span>
                <span className="block text-[11px] opacity-70">{count} patient{count === 1 ? '' : 's'}</span>
              </button>
            )
          })}
        </div>
      </PageHeader>

      <SectionTitle title={day === todayKey ? 'Today’s queue' : new Date(`${day}T00:00`).toLocaleDateString('en-PH', { weekday: 'long', month: 'long', day: 'numeric' })} description={appts.length ? `${appts.filter((a) => a.status === 'booked' || a.status === 'checked_in').length} still to see` : undefined} />
      {appts.length === 0 ? <Card><Empty icon={Stethoscope} title="No patients booked" text="Open slots for this day appear to patients on the booking page." /></Card> : (
        <ol className="relative space-y-3 before:absolute before:top-6 before:bottom-6 before:left-[87px] before:hidden before:w-px before:bg-gradient-to-b before:from-gold before:via-line before:to-line md:before:block">
          {appts.map((a, idx) => {
            const p = patientById.get(a.patient_id)
            const rec = db.medical_record.find((r) => r.appointment_id === a.appointment_id)
            const allergies = db.patient_allergy.filter((x) => x.patient_id === a.patient_id)
            const room = a.slot.room_id ? roomById.get(a.slot.room_id) : null
            const nextUp = appts.find((x) => x.status === 'checked_in') ?? appts.find((x) => x.status === 'booked')
            const isNext = nextUp?.appointment_id === a.appointment_id
            const done = a.status === 'completed' || a.status === 'no_show'
            return (
              <li key={a.appointment_id} className="animate-rise relative flex flex-col gap-3 md:flex-row md:items-stretch md:gap-6" style={{ animationDelay: `${idx * 60}ms` }}>
                <div className="flex w-20 shrink-0 items-center gap-3 md:flex-col md:items-end md:justify-center md:gap-0 md:text-right">
                  <p className={cx('font-display text-lg font-bold', done && 'text-muted')}>{fmtTime(a.slot.start_time)}</p>
                  {room && <p className="text-xs text-muted">{room.room_number}</p>}
                </div>
                <span className={cx('absolute top-1/2 left-[81px] z-10 hidden size-3.5 -translate-y-1/2 rounded-full ring-4 ring-canvas md:block', isNext ? 'bg-gold' : done ? 'bg-emerald-500' : 'bg-line')}>
                  {isNext && <span className="absolute inset-0 animate-ping rounded-full bg-gold/70" />}
                </span>
                <div className={cx('spotlight flex flex-1 flex-col gap-4 rounded-2xl border bg-surface p-4 shadow-[0_8px_24px_-12px_rgba(0,20,60,0.08)] transition duration-300 hover:-translate-y-0.5 md:ml-4 md:flex-row md:items-center', isNext ? 'border-gold/70 ring-4 ring-gold/15' : 'border-line', done && 'opacity-75')}>
                  <div className="flex min-w-0 flex-1 items-center gap-3">
                    <Avatar name={name(a.patient_id)} />
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <button onClick={() => go(`patients/${a.patient_id}`)} className="cursor-pointer font-semibold hover:text-brand">{name(a.patient_id)}</button>
                        <Status value={a.status} />
                        {isNext && <Badge tone="gold">Up next</Badge>}
                        {allergies.length > 0 && <Badge tone="red"><AlertOctagon className="size-3" />{allergies.length} allerg{allergies.length > 1 ? 'ies' : 'y'}</Badge>}
                      </div>
                      <p className="truncate text-sm text-muted"><span className="capitalize">{p?.affiliation}</span>{p?.department_id && ` · ${deptById.get(p.department_id)?.code}`}{age(p?.date_of_birth ?? null) != null && ` · ${age(p!.date_of_birth)} yrs`} · {a.reason_for_visit}</p>
                    </div>
                  </div>
                  <div className="flex shrink-0 flex-wrap gap-2">
                    {a.status === 'booked' && (
                      <>
                        <Button size="sm" variant="ghost" icon={UserX} onClick={() => run(() => actions.setAppointmentStatus(a.appointment_id, 'no_show'), 'Marked as missed.')}>Missed</Button>
                        <Button size="sm" variant="outline" icon={UserCheck} onClick={() => run(() => actions.setAppointmentStatus(a.appointment_id, 'checked_in'), `${name(a.patient_id)} checked in.`)}>Check in</Button>
                      </>
                    )}
                    {(a.status === 'checked_in') && <Button size="sm" variant={isNext ? 'accent' : 'primary'} icon={ClipboardPlus} onClick={() => openVisit(a.appointment_id)}>{rec ? 'Continue visit' : 'Start visit'}</Button>}
                    {a.status === 'completed' && rec && <Button size="sm" variant="outline" icon={FileHeart} onClick={() => go(`encounter/${rec.record_id}`)}>View chart</Button>}
                  </div>
                </div>
              </li>
            )
          })}
        </ol>
      )}

      {drafts.length > 0 && (
        <div className="mt-10">
          <SectionTitle title="Unfinished charts" description="Finalize these so patients can see their records." />
          <div className="grid gap-3 md:grid-cols-2">
            {drafts.map((r) => (
              <button key={r.record_id} onClick={() => go(`encounter/${r.record_id}`)} className="spotlight flex cursor-pointer items-center gap-4 rounded-2xl border border-gold/50 bg-gradient-to-r from-gold-100/70 to-surface p-4 text-left transition duration-300 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-gold/10 dark:from-gold/10">
                <span className="grid size-10 place-items-center rounded-xl bg-gold text-navy-950"><FilePen className="size-5" /></span>
                <div className="min-w-0 flex-1"><p className="font-semibold">{name(r.patient_id)}</p><p className="truncate text-sm text-muted">{r.chief_complaint} · {fmtDateTime(r.visited_at)}</p></div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
