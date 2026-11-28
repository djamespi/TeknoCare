import { useMemo, useState } from 'react'
import { CalendarPlus, Clock, UserCheck, MapPin } from 'lucide-react'
import { ActionButton, Button, Card, Field, Input, Modal, PageHeader, Select, Tabs, cx } from '../../components/ui'
import { dayKey, fmtTime } from '../../data/format'
import { useLookups, useStore } from '../../data/store'
import { useNav } from '../../nav'

export function Schedule() {
  const { db, me, actions } = useStore()
  const { run } = useNav()
  const { name, providerName, roomById, bookedSlots } = useLookups()
  const isAdmin = me!.user_type === 'admin'
  const [providerId, setProviderId] = useState(isAdmin ? db.provider.find(p => p.eligible)?.provider_id ?? 0 : me!.user_id)
  const [week, setWeek] = useState('0')
  const [open, setOpen] = useState(false)
  const defaultRoom = db.slot.find((s) => s.provider_id === providerId)?.room_id ?? db.clinic_room[0]?.room_id
  const [f, setF] = useState({ date: dayKey(new Date(Date.now() + 86_400_000 * 7).toISOString()), from: '08:00', to: '12:00', minutes: '30', room: String(defaultRoom ?? '') })
  const days = useMemo(() => {
    const d = new Date()
    d.setHours(0, 0, 0, 0)
    d.setDate(d.getDate() - ((d.getDay() + 6) % 7) + Number(week) * 7)
    return Array.from({ length: 5 }, (_, i) => new Date(d.getTime() + i * 86_400_000))
  }, [week])
  const apptBySlot = new Map(db.appointment.filter((a) => a.status !== 'canceled').map((a) => [a.slot_id, a]))
  const slots = db.slot.filter((s) => s.provider_id === providerId)

  return (
    <div>
      <PageHeader title={isAdmin ? 'Provider schedules' : 'Your schedule'} description="Open slots are bookable by patients. Select an open slot to close it, or a closed slot to reopen it." action={<Button variant="accent" icon={CalendarPlus} disabled={!providerId} onClick={() => setOpen(true)}>Publish slots</Button>}
        stats={(() => {
          const inWeek = slots.filter((s) => days.some((d) => dayKey(d.toISOString()) === dayKey(s.start_time)))
          const booked = inWeek.filter((s) => bookedSlots.has(s.slot_id)).length
          return [
            { icon: CalendarPlus, label: 'Slots this week', value: inWeek.length },
            { icon: UserCheck, label: 'Booked', value: booked },
            { icon: Clock, label: 'Utilization', value: inWeek.length ? Math.round((booked / inWeek.length) * 100) : 0, format: (n: number) => `${Math.round(n)}%` },
          ]
        })()} />
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Tabs value={week} onChange={setWeek} items={[{ value: '-1', label: 'Last week' }, { value: '0', label: 'This week' }, { value: '1', label: 'Next week' }, { value: '2', label: 'In 2 weeks' }]} />
        <div className="flex items-center gap-3">
          {isAdmin && (
            <Select className="w-64" value={providerId} onChange={(e) => setProviderId(Number(e.target.value))}>
              {!providerId && <option value={0}>No eligible providers</option>}{db.provider.filter(p => p.eligible).map((p) => <option key={p.provider_id} value={p.provider_id}>{providerName(p.provider_id)}</option>)}
            </Select>
          )}
        </div>
      </div>
      <div className="mb-4 flex flex-wrap gap-4 text-xs text-muted">
        <span className="flex items-center gap-1.5"><span className="size-3 rounded border border-line bg-surface" />Open</span>
        <span className="flex items-center gap-1.5"><span className="size-3 rounded bg-navy" />Booked</span>
        <span className="flex items-center gap-1.5"><span className="size-3 rounded bg-raised" />Closed</span>
      </div>
      <div className="grid gap-3 overflow-x-auto md:grid-cols-5">
        {days.map((d) => {
          const list = slots.filter((s) => dayKey(s.start_time) === dayKey(d.toISOString())).sort((a, b) => a.start_time.localeCompare(b.start_time))
          const isToday = dayKey(d.toISOString()) === dayKey(new Date().toISOString())
          return (
            <Card key={d.toISOString()} className={cx('animate-rise p-3', isToday && 'ring-2 ring-gold')}>
              <div className="mb-3 px-1">
                <p className="text-xs font-semibold text-muted">{d.toLocaleDateString('en-PH', { weekday: 'long' })}</p>
                <p className="font-display text-lg font-bold">{d.toLocaleDateString('en-PH', { month: 'short', day: 'numeric' })}</p>
              </div>
              {list.length === 0 ? <p className="px-1 py-6 text-center text-xs text-muted">No slots</p> : (
                <div className="space-y-1.5">
                  {list.map((s) => {
                    const a = apptBySlot.get(s.slot_id)
                    const past = new Date(s.start_time) < new Date()
                    return (
                      <ActionButton key={s.slot_id} disabled={!!a || past} onClick={() => run(() => actions.toggleSlot(s.slot_id), s.is_active ? 'Slot closed.' : 'Slot reopened.')}
                        title={a ? `${name(a.patient_id)}: ${a.reason_for_visit}` : undefined}
                        className={cx('flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-xs transition',
                          a ? 'bg-gradient-to-r from-navy to-navy-700 text-white shadow-sm shadow-navy/20 dark:from-navy-700 dark:to-navy-700' : s.is_active ? 'cursor-pointer border border-line bg-surface hover:translate-x-0.5 hover:border-gold hover:bg-gold-100/40' : 'cursor-pointer bg-raised text-muted line-through',
                          past && !a && 'opacity-45')}>
                        <span className="font-semibold">{fmtTime(s.start_time)}</span>
                        {a && <span className="truncate opacity-80">{name(a.patient_id).split(' ')[0]}</span>}
                      </ActionButton>
                    )
                  })}
                </div>
              )}
              {list.length > 0 && <p className="mt-3 px-1 text-[11px] text-muted"><MapPin className="mr-1 inline size-3" />{roomById.get(list[0].room_id ?? 0)?.room_number ?? 'No room'} · {list.filter((s) => bookedSlots.has(s.slot_id)).length}/{list.length} booked</p>}
            </Card>
          )
        })}
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title="Publish new slots" description={`For ${providerName(providerId)}. Choose an active room and a time range without conflicts.`}>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Date" className="col-span-2"><Input type="date" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} /></Field>
          <Field label="From"><Input type="time" value={f.from} onChange={(e) => setF({ ...f, from: e.target.value })} /></Field>
          <Field label="To"><Input type="time" value={f.to} onChange={(e) => setF({ ...f, to: e.target.value })} /></Field>
          <Field label="Slot length"><Select value={f.minutes} onChange={(e) => setF({ ...f, minutes: e.target.value })}><option value="15">15 minutes</option><option value="30">30 minutes</option><option value="60">1 hour</option></Select></Field>
          <Field label="Room"><Select value={f.room} onChange={(e) => setF({ ...f, room: e.target.value })}><option value="">No room</option>{db.clinic_room.filter((r) => r.is_active).map((r) => <option key={r.room_id} value={r.room_id}>{r.room_number}</option>)}</Select></Field>
          <Button className="col-span-2" icon={Clock} onClick={async () => {
            let n = 0
            if (await run(async () => { n = await actions.addSlots(providerId, f.room ? Number(f.room) : null, f.date, f.from, f.to, Number(f.minutes)) })) {
              setOpen(false)
              run(() => {}, n ? `Published ${n} slot${n > 1 ? 's' : ''}.` : 'Those times already exist.')
            }
          }}>Publish</Button>
        </div>
      </Modal>
    </div>
  )
}
