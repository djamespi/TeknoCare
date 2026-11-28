import { CalendarDays, Check, Send, UserCheck, Users, Wallet } from 'lucide-react'
import { Avatar, Badge, Button, Card, Empty, PageHeader, SectionTitle, cx } from '../../components/ui'
import { dayKey, peso, relative } from '../../data/format'
import { useLookups, useStore } from '../../data/store'
import { useNav } from '../../nav'

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
