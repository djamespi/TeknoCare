import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { AccountStatus, AppointmentStatus, DB, EmergencyContact, MedicalRecord, PrescriptionItem, ReferralStatus, User, UserProfile, UserSettings, VitalSign } from './types'

export class DomainError extends Error {}

type Session = {
  actor: number | null; db: DB | null; csrf: string; demo: boolean;
  next_open: { start: string; provider: string } | null; open_referrals: number;
}
const tableNames = [
  'department', 'user', 'patient', 'provider', 'user_profile', 'user_settings',
  'emergency_contact', 'patient_allergy', 'clinic_room', 'slot', 'appointment',
  'medical_record', 'vital_sign', 'diagnosis', 'record_diagnosis', 'medication',
  'prescription', 'prescription_item', 'referral', 'academic_term', 'student_charge', 'audit_log',
] as const satisfies readonly (keyof DB)[]
const emptyDb = Object.fromEntries(tableNames.map(name => [name, []])) as unknown as DB

async function fetchSession(): Promise<Session> {
  const response = await fetch('/portal/session/', { cache: 'no-store' })
  if (!response.ok) throw new DomainError('Could not open the clinic workspace.')
  return response.json()
}

function useDbState() {
  const [session, setSession] = useState<Session | null>(null)
  const [failed, setFailed] = useState(false)
  const db = session?.db ?? emptyDb
  const me = db.user.find(user => user.user_id === session?.actor) ?? null
  useEffect(() => {
    let alive = true
    fetchSession().then(next => { if (alive) setSession(next) }, () => { if (alive) setFailed(true) })
    return () => { alive = false }
  }, [])

  const csrf = session?.csrf
  const send = useCallback(async <T,>(operation: string, values: object = {}): Promise<T> => {
    const response = await fetch('/portal/actions/' + operation + '/', {
      method: 'POST', cache: 'no-store',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf ?? '' },
      body: JSON.stringify(values),
    })
    const payload = await response.json().catch(() => null)
    if (!response.ok) throw new DomainError(payload?.error ?? 'Reload the page and try again.')
    setSession(await fetchSession())
    return payload.result
  }, [csrf])

  const actions = useMemo(() => {
    const recordVersion = (id: number) => db.medical_record.find(row => row.record_id === id)?.version
    const slotVersion = (id: number) => db.slot.find(row => row.slot_id === id)?.version
    const changeDiagnosis = (operation: 'primary' | 'remove', diagnosis: number) => {
      const record = db.record_diagnosis.find(row => row.record_diagnosis_id === diagnosis)?.record_id
      return send('change-diagnosis', { operation, diagnosis, version: record ? recordVersion(record) : null })
    }
    return {
      login: (university_id: string, password: string) => send('login', { university_id, password }),
      register: (values: Record<string, string>) => send('register', values),
      logout: () => send('logout'),
      bookAppointment: (slot_id: number, reason: string) => send('book', { slot_id, reason, version: slotVersion(slot_id) }),
      cancelAppointment: (id: number) => send('cancel-booking', { id }),
      setAppointmentStatus: (id: number, status: AppointmentStatus) => send('appointment-status', { id, status }),
      startRecord: (id: number) => send<number>('open-encounter', { id }),
      updateRecord: (id: number, notes: Partial<MedicalRecord>) => send('save-notes', { id, notes, version: recordVersion(id) }),
      saveVitals: (id: number, measurements: Omit<VitalSign, 'vital_id' | 'record_id' | 'recorded_by_user_id' | 'recorded_at'>) => send('save-vitals', { id, measurements, version: recordVersion(id) }),
      addDiagnosis: (id: number, diagnosis: number) => send('change-diagnosis', { operation: 'add', diagnosis, id, version: recordVersion(id) }),
      setPrimaryDiagnosis: (id: number) => changeDiagnosis('primary', id),
      removeDiagnosis: (id: number) => changeDiagnosis('remove', id),
      addPrescriptionItem: (id: number, item: Omit<PrescriptionItem, 'item_id' | 'prescription_id'>) => {
        const draft = db.prescription.find(row => row.record_id === id && row.status === 'draft')
        return send('add-prescription-item', { id, item, prescription_id: draft?.prescription_id, version: draft?.version })
      },
      removePrescriptionItem: (id: number) => {
        const item = db.prescription_item.find(row => row.item_id === id)
        const prescription = db.prescription.find(row => row.prescription_id === item?.prescription_id)
        return send('delete-prescription-item', { id, version: prescription?.version })
      },
      prescriptionStatus: (id: number, operation: 'issue' | 'discard') => {
        const prescription = db.prescription.find(row => row.prescription_id === id)
        return send('prescription-status', { id, operation, version: prescription?.version })
      },
      addReferral: (id: number, destination: string, reason: string) => send('referral', { operation: 'add', id, destination, reason }),
      setReferralStatus: (id: number, status: ReferralStatus) => send('referral', { operation: 'update', id, status }),
      finalizeRecord: (id: number) => send('finalize', { id, version: recordVersion(id) }),
      updateBirthDate: (date_of_birth: string | null) => send('birth-date', { date_of_birth }),
      addContact: (values: Omit<EmergencyContact, 'contact_id' | 'patient_id'>) => send('contact', values),
      setPrimaryContact: (id: number) => send('contact', { id }),
      removeContact: (id: number) => send('remove-contact', { id }),
      updateProfile: (values: Partial<UserProfile>) => send('profile', values),
      updateSettings: (_user: number, values: Partial<UserSettings>) => send('preferences', values),
      setAccountStatus: (id: number, status: AccountStatus) => send('account-status', { id, status }),
      addProvider: (values: Record<string, string>) => send<number>('add-provider', values),
      changeCharge: (id: number, operation: 'post' | 'void', status: string, reason: string) =>
        send('change-charge', { id, operation, status, reason, confirm: true }),
      addSlots: (provider: number, room: number | null, date: string, from: string, to: string, minutes: number) =>
        send<number>('add-slots', { provider, room, date, from, to, minutes }),
      toggleSlot: (id: number) => send('toggle-slot', { id, version: slotVersion(id) }),
      saveReference: (table: keyof DB, entry: object, id?: number) => send('save-reference', { table, entry, id }),
    }
  }, [db, send])
  return { db, me, actions, pending: !session && !failed, failed, demo: session?.demo ?? false,
    nextOpen: session?.next_open, openReferrals: session?.open_referrals ?? 0 }
}

const Store = createContext<ReturnType<typeof useDbState> | null>(null)
export function StoreProvider({ children }: { children: ReactNode }) {
  const state = useDbState()
  return <Store.Provider value={state}>{children}</Store.Provider>
}
export function useStore() {
  const state = useContext(Store)
  if (!state) throw new Error('StoreProvider is missing')
  return state
}

export function useLookups() {
  const { db } = useStore()
  return useMemo(() => {
    const userById = new Map(db.user.map((u) => [u.user_id, u]))
    const slotById = new Map(db.slot.map((s) => [s.slot_id, s]))
    const roomById = new Map(db.clinic_room.map((r) => [r.room_id, r]))
    const providerById = new Map(db.provider.map((p) => [p.provider_id, p]))
    const patientById = new Map(db.patient.map((p) => [p.patient_id, p]))
    const deptById = new Map(db.department.map((d) => [d.department_id, d]))
    const medById = new Map(db.medication.map((m) => [m.medication_id, m]))
    const dxById = new Map(db.diagnosis.map((m) => [m.diagnosis_id, m]))
    const termById = new Map(db.academic_term.map((t) => [t.term_id, t]))
    const recordById = new Map(db.medical_record.map((r) => [r.record_id, r]))
    const bookedSlots = new Set(db.appointment.filter((a) => a.status !== 'canceled').map((a) => a.slot_id))
    const name = (id: number | null | undefined) => {
      const u = id != null ? userById.get(id) : undefined
      return u ? (`${u.fname} ${u.lname}`.trim() || u.school_id || 'Clinic account') : 'System'
    }
    const providerName = (id: number) => {
      const p = providerById.get(id)
      const n = name(id)
      return p?.provider_type === 'nurse' ? `Nurse ${n}` : `Dr. ${n}`
    }
    return { userById, slotById, roomById, providerById, patientById, deptById, medById, dxById, termById, recordById, bookedSlots, name, providerName }
  }, [db])
}
