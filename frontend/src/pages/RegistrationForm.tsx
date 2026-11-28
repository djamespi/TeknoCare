import { useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { Button, Field, Input, Textarea } from '../components/ui'
import { DomainError, useStore } from '../data/store'
import { useNav } from '../nav'

const emptyValues = {
  university_id: '', first_name: '', last_name: '', email: '',
  emergency_contact_name: '', emergency_contact_relationship: '', emergency_contact: '',
  medical_history_summary: '', password1: '', password2: '',
}

const steps = [
  { title: 'Student details', fields: ['first_name', 'last_name', 'university_id', 'email'] },
  { title: 'Emergency contact and health', fields: ['emergency_contact_name', 'emergency_contact_relationship', 'emergency_contact', 'medical_history_summary'] },
  { title: 'Set your password', fields: ['password1', 'password2'] },
]

export default function RegistrationForm({ onRegistered }: { onRegistered: (id: string) => void }) {
  const { actions } = useStore()
  const { toast } = useNav()
  const [values, setValues] = useState(emptyValues)
  const [step, setStep] = useState(0)
  const [busy, setBusy] = useState(false)
  const [feedback, setFeedback] = useState('')
  const heading = useRef<HTMLHeadingElement>(null)
  const finalStep = step === steps.length - 1

  const field = (key: keyof typeof emptyValues) => ({
    name: key,
    value: values[key],
    onChange: (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      const value = event.target.value
      setValues(previous => ({ ...previous, [key]: value }))
      setFeedback('')
    },
  })

  function goToStep(index: number) {
    setStep(index)
    requestAnimationFrame(() => heading.current?.focus())
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    setFeedback('')
    if (!finalStep) {
      goToStep(step + 1)
      return
    }
    if (values.password1 !== values.password2) {
      setFeedback('Passwords must match.')
      return
    }
    setBusy(true)
    try {
      await actions.register(values)
      onRegistered(values.university_id)
      setStep(0)
      setValues(emptyValues)
      toast('Student account created. Sign in with your university ID.')
    } catch (error) {
      if (error instanceof DomainError) {
        const fieldErrors = error.fieldErrors
        const firstInvalidStep = fieldErrors
          ? steps.findIndex(({ fields }) => fields.some(field => field in fieldErrors))
          : -1
        if (firstInvalidStep >= 0) goToStep(firstInvalidStep)
        setFeedback(error.message)
      } else {
        setFeedback('Registration could not be completed. Check your connection and try again.')
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} aria-labelledby="registration-step" aria-busy={busy} className="rounded-2xl border border-line bg-white p-5 sm:p-6">
      <header className="space-y-3">
        <p className="w-fit rounded-full bg-navy px-3 py-1 text-xs font-semibold text-gold">Step {step + 1} of {steps.length}</p>
        <h3 id="registration-step" ref={heading} tabIndex={-1} className="font-display text-xl font-bold text-navy">
          {steps[step].title}
        </h3>
      </header>
      {feedback && (
        <p role="alert" className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-800">{feedback}</p>
      )}
      <fieldset key={step} disabled={busy} className="mt-5 grid min-w-0 gap-x-4 gap-y-5 sm:grid-cols-2">
        {step === 0 && <>
          <Field label="First name"><Input required maxLength={50} autoComplete="given-name" {...field('first_name')} /></Field>
          <Field label="Last name"><Input required maxLength={50} autoComplete="family-name" {...field('last_name')} /></Field>
          <Field label="University ID" hint="Use the ID on your student card. This is your sign-in ID." className="sm:col-span-2">
            <Input required maxLength={20} autoComplete="username" {...field('university_id')} />
          </Field>
          <Field label="Email" hint="Use an email address you can access." className="sm:col-span-2">
            <Input required maxLength={100} type="email" autoComplete="email" {...field('email')} />
          </Field>
        </>}
        {step === 1 && <>
          <Field label="Emergency contact name" hint="Who should the clinic call in an emergency?" className="sm:col-span-2">
            <Input required maxLength={150} autoComplete="section-emergency name" {...field('emergency_contact_name')} />
          </Field>
          <Field label="Relationship" hint="For example, parent or guardian.">
            <Input required maxLength={50} {...field('emergency_contact_relationship')} />
          </Field>
          <Field label="Emergency contact phone">
            <Input required maxLength={30} type="tel" autoComplete="section-emergency tel" {...field('emergency_contact')} />
          </Field>
          <Field label="Medical history (optional)" hint="Mention any allergies, ongoing conditions, or regular medications." className="border-t border-line pt-5 sm:col-span-2">
            <Textarea {...field('medical_history_summary')} />
          </Field>
        </>}
        {finalStep && <>
          <Field label="Password" hint="Use 8+ characters. Avoid common passwords, personal details, and numbers-only passwords." className="sm:col-span-2">
            <Input required minLength={8} type="password" autoComplete="new-password" {...field('password1')} />
          </Field>
          <Field label="Confirm password" className="sm:col-span-2">
            <Input required type="password" autoComplete="new-password" {...field('password2')} />
          </Field>
        </>}
      </fieldset>
      <div className="mt-6 flex gap-3 border-t border-line pt-5">
        {step > 0 && <Button type="button" variant="outline" size="lg" disabled={busy} onClick={() => { setFeedback(''); goToStep(step - 1) }}>Back</Button>}
        <Button type="submit" size="lg" loading={busy} className="flex-1">
          {finalStep ? 'Submit' : 'Next'}
        </Button>
      </div>
    </form>
  )
}
