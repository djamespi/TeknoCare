import { useLookups, useStore } from './store'

export function usePatientData() {
  const { db, me } = useStore()
  const L = useLookups()
  const pid = me!.user_id
  const appts = db.appointment
    .filter((a) => a.patient_id === pid)
    .map((a) => ({ ...a, slot: L.slotById.get(a.slot_id)! }))
    .sort((a, b) => a.slot.start_time.localeCompare(b.slot.start_time))
  const records = db.medical_record.filter((r) => r.patient_id === pid && r.status === 'finalized').sort((a, b) => b.visited_at.localeCompare(a.visited_at))
  return { pid, appts, records, patient: L.patientById.get(pid), ...L }
}
