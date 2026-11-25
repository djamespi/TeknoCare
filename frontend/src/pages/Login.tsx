import { useState } from 'react'
import hero from '../assets/clinic-hero.jpg'
import { Button, Field, Input, Logo, Tabs } from '../components/ui'
import { useStore } from '../data/store'
import { useNav } from '../nav'

export default function Login() {
  const { actions } = useStore()
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
        <img src={hero} alt="A campus nurse speaking with a student at the TeknoCare clinic" className="absolute inset-0 h-full w-full scale-105 object-cover" />
        <div className="absolute inset-0 bg-gradient-to-t from-navy-950 via-navy-950/60 to-navy/20" />
        <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="aurora-a absolute -bottom-40 -left-24 size-[520px] rounded-full bg-navy-700/60 blur-[120px]" />
          <div className="aurora-b absolute top-1/3 -right-32 size-[380px] rounded-full bg-gold/20 blur-[110px]" />
          <div className="noise absolute inset-0" />
        </div>


        <div className="relative flex h-full flex-col justify-between p-12 text-white">
          <Logo light />
          <div className="max-w-lg">
            <p className="animate-rise mb-5 inline-flex items-center gap-2 rounded-full bg-white/10 px-3.5 py-1.5 text-[13px] font-medium ring-1 ring-white/15 backdrop-blur">
              <span className="relative flex size-2"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-gold opacity-70" /><span className="relative inline-flex size-2 rounded-full bg-gold" /></span> CIT-University Health Services
            </p>
            <h1 className="animate-blur-in text-[56px] leading-[1.02] font-bold">
              CIT-University <span className="text-shine">clinic</span>
            </h1>
            <p className="animate-rise mt-5 text-[17px] leading-relaxed text-white/75" style={{ animationDelay: '150ms' }}>
              Book appointments, review visit summaries and see charges posted to tuition.
            </p>

          </div>
        </div>
      </div>

      <div className="relative flex flex-col overflow-hidden px-6 py-10 sm:px-12 lg:px-16">
        <div aria-hidden className="dot-grid pointer-events-none absolute inset-0 [--tc-brand:#002870] [mask-image:radial-gradient(ellipse_at_top_right,#000,transparent_60%)]" />
        <div aria-hidden className="pointer-events-none absolute -top-32 -right-32 size-80 rounded-full bg-gold/25 blur-[100px]" />
        <div className="relative lg:hidden"><Logo /></div>
        <div className="animate-rise relative mx-auto my-auto w-full max-w-md py-10">
          <h2 className="text-[34px] leading-tight font-bold text-navy">{mode === 'in' ? 'Sign in to TeknoCare' : 'Create your account'}</h2>
          <p className="mt-2 text-[15px] text-[#5b6478]">{mode === 'in' ? 'Use your university ID to sign in.' : 'Student registration uses fictional details.'}</p>
          <div className="my-7"><Tabs value={mode} onChange={setMode} items={[{ value: 'in', label: 'Sign in' }, { value: 'up', label: 'Register' }]} /></div>
            {mode === 'in' ? (
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
        </div>
        <p className="relative text-center text-xs text-[#5b6478]">Cebu Institute of Technology – University · Health Services Center</p>
      </div>
    </div>
  )
}
