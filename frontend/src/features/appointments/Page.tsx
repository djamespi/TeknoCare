import { useState } from 'react'
import { CalendarCheck, CalendarPlus, Clock, FileHeart, CircleCheck } from 'lucide-react'
import { Button, Card, Empty, Modal, PageHeader, Status, Tabs, cx } from '../../components/ui'
import { fmtDateTime, fmtTime } from '../../data/format'
import { useStore } from '../../data/store'
import { useNav } from '../../nav'
import { usePatientData } from '../../data/usePatientData'

function DateBlock({ iso, muted }: { iso: string; muted?: boolean }) {
  const d = new Date(iso)
  return (
    <div className={cx('grid w-14 shrink-0 place-items-center rounded-xl py-2 text-center', muted ? 'bg-raised text-muted' : 'bg-navy text-white dark:bg-navy-700')}>
      <span className="text-[11px] font-semibold opacity-75">{d.toLocaleDateString('en-PH', { month: 'short' })}</span>
      <span className="font-display text-xl leading-none font-bold">{d.getDate()}</span>
    </div>
  )
}

export function Appointments() {
  const { actions, db } = useStore()
  const { go, run } = useNav()
  const { appts, providerName, roomById, providerById } = usePatientData()
  const [tab, setTab] = useState<'upcoming' | 'past' | 'canceled'>('upcoming')
  const [confirm, setConfirm] = useState<number | null>(null)
  const groups = {
    upcoming: appts.filter((a) => a.status === 'booked' || a.status === 'checked_in'),
    past: appts.filter((a) => a.status === 'completed' || a.status === 'no_show').reverse(),
    canceled: appts.filter((a) => a.status === 'canceled').reverse(),
  }
  const list = groups[tab]
  return (
    <div>
      <PageHeader title="Appointments" description="Everything you’ve booked with the clinic, past and upcoming." action={<Button icon={CalendarPlus} variant="accent" onClick={() => go('book')}>Book a visit</Button>}
        stats={[{ icon: CalendarCheck, label: 'Upcoming', value: groups.upcoming.length }, { icon: CircleCheck, label: 'Completed', value: groups.past.filter((a) => a.status === 'completed').length }, { icon: Clock, label: 'Canceled', value: groups.canceled.length }]} />
      <div className="mb-5">
        <Tabs value={tab} onChange={setTab} items={[{ value: 'upcoming', label: 'Upcoming', count: groups.upcoming.length }, { value: 'past', label: 'Past', count: groups.past.length }, { value: 'canceled', label: 'Canceled', count: groups.canceled.length }]} />
      </div>
      <Card className="divide-y divide-line">
        {list.length === 0 && <Empty icon={CalendarCheck} title={tab === 'upcoming' ? 'Nothing scheduled' : 'Nothing here yet'} text={tab === 'upcoming' ? 'Book a visit and it will show up here.' : undefined} />}
        {list.map((a, idx) => {
          const rec = db.medical_record.find((r) => r.appointment_id === a.appointment_id && r.status === 'finalized')
          const room = a.slot.room_id ? roomById.get(a.slot.room_id) : null
          return (
            <div key={a.appointment_id} className={cx('animate-rise relative flex flex-col gap-4 p-5 transition hover:bg-raised/40 sm:flex-row sm:items-center', tab === 'upcoming' && idx === 0 && 'bg-gold-100/40 dark:bg-gold/5')} style={{ animationDelay: `${idx * 50}ms` }}>
              {tab === 'upcoming' && idx === 0 && <span className="absolute top-4 bottom-4 left-0 w-1 rounded-r-full bg-gold" />}
              <DateBlock iso={a.slot.start_time} muted={tab !== 'upcoming'} />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-semibold">{fmtTime(a.slot.start_time)} · {providerById.get(a.slot.provider_id)?.specialization}</p>
                  <Status value={a.status} />
                </div>
                <p className="mt-0.5 text-sm text-muted">{providerName(a.slot.provider_id)}{room && ` · ${room.building}, ${room.room_number}`}</p>
                <p className="mt-1 text-sm">{a.reason_for_visit}</p>
                {a.canceled_at && <p className="mt-1 text-xs text-muted">Canceled {fmtDateTime(a.canceled_at)}</p>}
              </div>
              <div className="flex gap-2">
                {rec && <Button variant="outline" size="sm" icon={FileHeart} onClick={() => go(`record/${rec.record_id}`)}>View record</Button>}
                {a.can_cancel && <>
                  <Button variant="outline" size="sm" data-page-load onClick={() => window.location.assign(`/appointments/${a.appointment_id}/reschedule/`)}>Reschedule</Button>
                  <Button variant="danger" size="sm" onClick={() => setConfirm(a.appointment_id)}>Cancel</Button>
                </>}
              </div>
            </div>
          )
        })}
      </Card>
      <Modal open={confirm != null} onClose={() => setConfirm(null)} title="Cancel this visit?" description="Your slot will be released so another student can book it.">
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setConfirm(null)}>Keep visit</Button>
          <Button onClick={async () => { if (await run(() => actions.cancelAppointment(confirm!), 'Visit canceled.')) setConfirm(null) }}>Yes, cancel</Button>
        </div>
      </Modal>
    </div>
  )
}
