import { useState } from 'react'
import { CalendarClock, HeartPulse, ShieldCheck, Stethoscope } from 'lucide-react'
import { clinicStatus, fmtTime, relative } from '../data/format'
import hero from '../../../static/images/clinic-hero.jpg'
import { Button, Field, Input, Logo, Tabs } from '../components/ui'
import { useStore } from '../data/store'
import { useNav } from '../nav'
import RegistrationForm from './RegistrationForm'

export default function Login() {
  const { actions, demo, nextOpen } = useStore()
  const status = clinicStatus()
  const { run, segments } = useNav()
  const [mode, setMode] = useState<'in' | 'up'>(segments[0] === 'register' ? 'up' : 'in')
  const [id, setId] = useState('')
  const [pw, setPw] = useState('')
  const [busy, setBusy] = useState(false)
  return (
    <div className="grid min-h-screen bg-white lg:grid-cols-[1.05fr_1fr]">
      <div className="hidden bg-navy-950 lg:block">
        <div className="relative isolate flex min-h-[max(100svh,44rem)] flex-col justify-between gap-16 overflow-hidden p-12 text-white">
          <img src={hero} alt="A campus nurse speaking with a student at the TeknoCare clinic" className="login-photo absolute inset-0 -z-10 h-full w-full scale-105 object-cover" />
          <div className="absolute inset-0 -z-10 bg-gradient-to-t from-navy-950 via-navy-950/60 to-navy/20" />
          <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
            <div className="aurora-a absolute -bottom-40 -left-24 size-[520px] rounded-full bg-navy-700/60 blur-[120px]" />
            <div className="aurora-b absolute top-1/3 -right-32 size-[380px] rounded-full bg-gold/20 blur-[110px]" />
            <div className="noise absolute inset-0" />
            <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-b from-transparent to-navy-950" />
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
        <div aria-hidden className="pointer-events-none absolute -top-32 -right-32 size-80 rounded-full bg-gold/25 blur-[100px]" />
        <div className="relative lg:hidden"><Logo /></div>
        <div className="animate-rise relative mx-auto my-auto w-full max-w-md py-10">
          <h2 className="text-[34px] leading-tight font-bold text-navy">{mode === 'in' ? 'Welcome back' : 'Create your account'}</h2>
          <p className="mt-2 text-[15px] text-[#5b6478]">{mode === 'in' ? 'Use your university ID to sign in.' : demo ? 'Register a sample student with fictional details.' : 'Create a student account to book visits and view your records.'}</p>
          <div className="my-7"><Tabs value={mode} onChange={setMode} items={[{ value: 'in', label: 'Sign in' }, { value: 'up', label: 'Register' }]} /></div>
          {mode === 'in' && <>
            <form className="space-y-4" onSubmit={async (event) => {
              event.preventDefault()
              setBusy(true)
              await run(() => actions.login(id, pw))
              setBusy(false)
            }}>
              <Field label="University ID"><Input required value={id} onChange={event => setId(event.target.value)} autoComplete="username" /></Field>
              <Field label="Password"><Input required type="password" value={pw} onChange={event => setPw(event.target.value)} autoComplete="current-password" /></Field>
              <Button disabled={busy} size="lg" className="w-full" type="submit">Sign in</Button>
            </form>
            <p className="mt-6 text-sm text-muted">For password help, contact the clinic administrator.</p>
          </>}
          <div hidden={mode !== 'up'}>
            <RegistrationForm onRegistered={universityId => {
              setId(universityId)
              setPw('')
              setMode('in')
            }} />
          </div>
        </div>
        <p className="relative text-center text-xs text-[#5b6478]">Cebu Institute of Technology – University · Health Services Center</p>
      </div>
    </div>
  )
}
