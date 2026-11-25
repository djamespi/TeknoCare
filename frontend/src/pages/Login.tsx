import { useState } from 'react'
import { BadgeCheck, CalendarClock, GraduationCap, HeartPulse, ShieldCheck, Stethoscope, UserCog, UserRound } from 'lucide-react'
import { clinicStatus, fmtTime, relative } from '../data/format'
import hero from '../assets/clinic-hero.jpg'
import { Button, Field, Input, Logo, Tabs, cx } from '../components/ui'
import { useStore } from '../data/store'
import { useNav } from '../nav'

const sampleAccounts = [
  { id: '21-4587-213', label: 'Student', sub: 'Andrea Lim · CCS', icon: GraduationCap },
  { id: 'FAC-0712', label: 'Faculty', sub: 'Elena Sarmiento · CASE', icon: UserRound },
  { id: 'MD-1021', label: 'Physician', sub: 'Dr. Ramon Abellana', icon: Stethoscope },
  { id: 'RN-2045', label: 'Nurse', sub: 'Liza Cabahug, RN', icon: BadgeCheck },
  { id: 'ADM-0001', label: 'Administrator', sub: 'Teresa Villanueva', icon: UserCog },
]

export default function Login() {
  const { actions, demo, nextOpen } = useStore()
  const status = clinicStatus()
  const { run, segments } = useNav()
  const [mode, setMode] = useState<'in' | 'up'>(segments[0] === 'register' ? 'up' : 'in')
  const [id, setId] = useState('')
  const [pw, setPw] = useState('')
  const [f, setF] = useState({ university_id:'', first_name:'', last_name:'', email:'',
    emergency_contact_name:'', emergency_contact_relationship:'', emergency_contact:'', password1:'', password2:'',
    medical_history_summary:'' })
  const field = (key: keyof typeof f) => ({ value:f[key], onChange:(event: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [key]:event.target.value }) })
  const [busy, setBusy] = useState(false)
  return (
    <div className="grid min-h-screen bg-white lg:grid-cols-[1.05fr_1fr]">
      <div className="relative hidden overflow-hidden lg:block">
        <img src={hero} alt="A campus nurse speaking with a student at the TeknoCare clinic" className="login-photo absolute inset-0 h-full w-full scale-105 object-cover" />
        <div className="absolute inset-0 bg-gradient-to-t from-navy-950 via-navy-950/60 to-navy/20" />
        <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="aurora-a absolute -bottom-40 -left-24 size-[520px] rounded-full bg-navy-700/60 blur-[120px]" />
          <div className="aurora-b absolute top-1/3 -right-32 size-[380px] rounded-full bg-gold/20 blur-[110px]" />
          <div className="noise absolute inset-0" />
        </div>


        {nextOpen && (
          <div className="animate-float absolute top-28 right-10 hidden w-64 rounded-2xl bg-white/10 p-4 text-white shadow-2xl ring-1 ring-white/20 backdrop-blur-xl xl:block">
            <div className="flex items-center gap-3">
              <span className="grid size-10 place-items-center rounded-xl bg-gold text-navy-950"><CalendarClock className="size-5" /></span>
              <div className="min-w-0">
                <p className="text-xs text-white/60">Next open slot · {relative(nextOpen.start)}</p>
                <p className="font-display text-lg leading-tight font-bold">{fmtTime(nextOpen.start)}</p>
              </div>
            </div>
            <p className="mt-3 truncate text-xs text-white/70">{nextOpen.provider}</p>
          </div>
        )}
        {demo && <div className="animate-float absolute top-56 right-44 hidden items-center gap-2 rounded-full bg-white/10 px-3.5 py-2 text-xs font-semibold text-white shadow-xl ring-1 ring-white/20 backdrop-blur-xl xl:flex" style={{ animationDuration: '7s', animationDelay: '1s' }}>
          <HeartPulse className="size-4 text-gold" /> {status.open ? 'Clinic is open now' : 'Walk-ins welcome on weekdays'}
        </div>}

        <div className="relative flex h-full flex-col justify-between p-12 text-white">
          <Logo light />
          <div className="max-w-lg">
            <p className="animate-rise mb-5 inline-flex items-center gap-2 rounded-full bg-white/10 px-3.5 py-1.5 text-[13px] font-medium ring-1 ring-white/15 backdrop-blur">
              <span className="relative flex size-2"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-gold opacity-70" /><span className="relative inline-flex size-2 rounded-full bg-gold" /></span> CIT-University Health Services
            </p>
            <h1 className="animate-blur-in text-[56px] leading-[1.02] font-bold">
              Care that keeps <span className="text-shine">Wildcats</span> well.
            </h1>
            <p className="animate-rise mt-5 text-[17px] leading-relaxed text-white/75" style={{ animationDelay: '150ms' }}>
              Book appointments, keep your health records in one place, and see clinic charges before they reach your tuition.
            </p>

            <div className="mt-10 grid grid-cols-3 gap-3">
              {[
                { icon: CalendarClock, t: demo ? 'Same-week slots' : 'Visit booking' },
                { icon: ShieldCheck, t: 'Private records' },
                { icon: Stethoscope, t: demo ? 'Licensed staff' : 'Clinic staff' },
              ].map(({ icon: I, t }, i) => (
                <div key={t} className="animate-rise rounded-2xl bg-white/[0.08] p-4 ring-1 ring-white/10 backdrop-blur-md transition duration-300 hover:-translate-y-1 hover:bg-white/[0.12]" style={{ animationDelay: `${250 + i * 80}ms` }}>
                  <I className="mb-3 size-5 text-gold" />
                  <p className="text-sm font-semibold">{t}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="relative flex flex-col overflow-hidden px-6 py-10 sm:px-12 lg:px-16">
        <div aria-hidden className="dot-grid pointer-events-none absolute inset-0 [--tc-brand:#002870] [mask-image:radial-gradient(ellipse_at_top_right,#000,transparent_60%)]" />
        <div aria-hidden className="pointer-events-none absolute -top-32 -right-32 size-80 rounded-full bg-gold/25 blur-[100px]" />
        <div className="relative lg:hidden"><Logo /></div>
        <div className="animate-rise relative mx-auto my-auto w-full max-w-md py-10">
          <h2 className="text-[34px] leading-tight font-bold text-navy">{mode === 'in' ? 'Welcome back' : 'Create your account'}</h2>
          <p className="mt-2 text-[15px] text-[#5b6478]">{mode === 'in' ? 'Use your university ID to sign in.' : demo ? 'Register a sample student with fictional details.' : 'Create a student account to book visits and view your records.'}</p>
          <div className="my-7"><Tabs value={mode} onChange={setMode} items={[{ value: 'in', label: 'Sign in' }, { value: 'up', label: 'Register' }]} /></div>
            {mode === 'in' ? (
            <form className="space-y-4" onSubmit={async (event) => {
              event.preventDefault()
              setBusy(true)
              await run(() => actions.login(id, pw))
              setBusy(false)
            }}>
              <Field label="University ID"><Input required value={id} onChange={event => setId(event.target.value)} autoComplete="username" /></Field>
              <Field label="Password"><Input id="portal-password" required type="password" value={pw} onChange={event => setPw(event.target.value)} autoComplete="current-password" /></Field>
              <Button disabled={busy} size="lg" className="w-full" type="submit">Sign in</Button>
            </form>
          ) : (
            <form className="grid grid-cols-2 gap-4" onSubmit={async (event) => {
              event.preventDefault()
              setBusy(true)
              if (await run(() => actions.register(f), 'Student account created. Sign in with your university ID.')) {
                setId(f.university_id)
                setF({ ...f, password1:'', password2:'' })
                setMode('in')
              }
              setBusy(false)
            }}>
              <Field label="First name"><Input required {...field('first_name')} /></Field>
              <Field label="Last name"><Input required {...field('last_name')} /></Field>
              <Field label="University ID" className="col-span-2"><Input required {...field('university_id')} /></Field>
              <Field label="Email" className="col-span-2"><Input required type="email" {...field('email')} /></Field>
              <Field label="Emergency contact name" className="col-span-2"><Input required {...field('emergency_contact_name')} /></Field>
              <Field label="Relationship"><Input required {...field('emergency_contact_relationship')} /></Field>
              <Field label="Phone"><Input required type="tel" {...field('emergency_contact')} /></Field>
              <Field label="Medical history (optional)" className="col-span-2"><Input {...field('medical_history_summary')} /></Field>
              <Field label="Password"><Input required type="password" autoComplete="new-password" {...field('password1')} /></Field>
              <Field label="Confirm password"><Input required type="password" autoComplete="new-password" {...field('password2')} /></Field>
              <Button disabled={busy} size="lg" className="col-span-2" type="submit">Create student account</Button>
            </form>
          )}
          {mode === 'in' && <p className="mt-6 text-sm text-muted">For password help, contact the clinic administrator.</p>}
          {demo && <div className="mt-10">
            <div className="mb-3 flex items-center gap-3 text-[13px] text-[#5b6478]">
              <span className="h-px flex-1 bg-[#e3e8f1]" /> Explore with a demo account <span className="h-px flex-1 bg-[#e3e8f1]" />
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {sampleAccounts.map(({ id: uid, label, sub, icon: I }, i) => (
                <button
                  key={uid}
                  onClick={() => { setId(uid); setMode('in'); document.getElementById('portal-password')?.focus() }}
                  className={cx('group flex cursor-pointer items-center gap-3 rounded-xl border border-[#e3e8f1] bg-white p-3 text-left transition duration-300 hover:-translate-y-0.5 hover:border-gold hover:shadow-lg hover:shadow-gold/15', i === sampleAccounts.length - 1 && 'sm:col-span-2')}
                >
                  <span className="grid size-9 place-items-center rounded-lg bg-navy-50 text-navy transition duration-300 group-hover:scale-110 group-hover:bg-navy group-hover:text-gold"><I className="size-4" /></span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-semibold text-[#0a0f1c]">{label}</span>
                    <span className="block truncate text-xs text-[#5b6478]">{sub}</span>
                  </span>
                </button>
              ))}
            </div>
          </div>}
        </div>
        <p className="relative text-center text-xs text-[#5b6478]">Cebu Institute of Technology – University · Health Services Center</p>
      </div>
    </div>
  )
}
