// Types mirror the TeknoCare Django/PostgreSQL schema (22 entities) one-to-one.

export type ISO = string

export type UserType = 'patient' | 'provider' | 'admin'
export type AccountStatus = 'active' | 'pending' | 'suspended'
export type Affiliation = 'student' | 'faculty' | 'staff'

export interface Department {
  department_id: number
  code: string
  name: string
  is_active: boolean
}

export interface User {
  user_id: number
  school_id: string
  fname: string
  lname: string
  email: string
  user_type: UserType
  account_status: AccountStatus
  created_at: ISO
}

export interface Patient {
  patient_id: number
  department_id: number | null
  affiliation: Affiliation | null
  date_of_birth: string | null
  medical_history_summary: string | null
  created_at: ISO
}

export interface Provider {
  provider_id: number
  provider_type: 'physician' | 'nurse' | 'dentist' | 'unverified'
  license_number: string | null
  specialization: string | null
  eligible: boolean
  is_active: boolean
  booking_photo?: 'mara-villareal' | 'joel-macaraeg'
}

export interface UserProfile {
  user_id: number
  phone_number: string | null
  home_address: string | null
  bio: string | null
}

export interface UserSettings {
  user_id: number
  dark_mode: boolean
  email_notifications: boolean
}

export interface EmergencyContact {
  contact_id: number
  patient_id: number
  full_name: string
  relationship: string
  phone_number: string
  is_primary: boolean
}

export type Severity = 'unknown' | 'mild' | 'moderate' | 'severe'
export interface PatientAllergy {
  allergy_id: number
  patient_id: number
  allergen: string
  reaction: string | null
  severity: Severity
  recorded_at: ISO
}

export interface ClinicRoom {
  room_id: number
  campus: string
  building: string
  room_number: string
  is_active: boolean
}

export interface Slot {
  slot_id: number
  version?: string
  bookable: boolean
  provider_id: number
  room_id: number | null
  start_time: ISO
  end_time: ISO
  is_active: boolean
}

export type AppointmentStatus = 'booked' | 'checked_in' | 'completed' | 'canceled' | 'no_show'
export interface Appointment {
  appointment_id: number
  patient_id: number
  slot_id: number
  reason_for_visit: string
  can_cancel: boolean
  status: AppointmentStatus
  created_at: ISO
  canceled_at: ISO | null
}

export type RecordStatus = 'draft' | 'finalized'
export interface MedicalRecord {
  record_id: number
  appointment_id: number | null
  patient_id: number
  provider_id: number
  chief_complaint: string
  affiliation_at_visit: Affiliation | null
  symptoms: string | null
  examination_notes: string | null
  treatment_plan: string | null
  status: RecordStatus
  visited_at: ISO
  finalized_at: ISO | null
  version?: string
  can_edit: boolean
  can_finalize: boolean
  can_record_vitals: boolean
  can_prescribe: boolean
  can_refer: boolean
}

export interface VitalSign {
  vital_id: number
  record_id: number
  recorded_by_user_id: number
  recorded_at: ISO
  temperature_c: number | null
  systolic_mmhg: number | null
  diastolic_mmhg: number | null
  pulse_bpm: number | null
  respiratory_rate: number | null
  oxygen_saturation_pct: number | null
  height_cm: number | null
  weight_kg: number | null
}

export interface Diagnosis {
  diagnosis_id: number
  code: string
  description: string
  coding_system: string
}

export interface RecordDiagnosis {
  record_diagnosis_id: number
  record_id: number
  diagnosis_id: number
  is_primary: boolean
  notes: string | null
}

export interface Medication {
  medication_id: number
  medication_code: string
  generic_name: string
  strength: string
  dosage_form: string
  is_active: boolean
}

export type PrescriptionStatus = 'draft' | 'issued' | 'canceled'
export interface Prescription {
  prescription_id: number
  version?: string
  record_id: number
  prescriber_id: number
  issued_at: ISO | null
  status: PrescriptionStatus
}

export interface PrescriptionItem {
  item_id: number
  prescription_id: number
  medication_id: number
  dose: string
  route: string
  frequency: string
  duration_days: number
  quantity: number
  quantity_unit: string
  instructions: string | null
}

export type ReferralStatus = 'pending' | 'canceled' | 'completed'
export interface Referral {
  referral_id: number
  record_id: number
  referred_by_provider_id: number
  destination: string
  reason: string
  status: ReferralStatus
  referred_at: ISO
}

export interface AcademicTerm {
  term_id: number
  academic_year: string
  semester: string
  start_date: string
  end_date: string
  is_open_for_charges: boolean
}

export type ChargeStatus = 'pending' | 'posted' | 'voided'
export interface StudentCharge {
  charge_id: number
  patient_id: number
  charge_code: string
  record_id: number
  term_id: number
  created_by_user_id: number
  description: string
  amount: number
  currency_code: string
  status: ChargeStatus
  billing_reference: string | null
  reversal_reference: string | null
  created_at: ISO
  posted_at: ISO | null
  voided_at: ISO | null
  void_reason: string | null
}

export interface AuditLog {
  log_id: number
  actor_user_id: number | null
  action_performed: string
  target_table: string
  target_record_id: number
  logged_at: ISO
}

export interface DB {
  department: Department[]
  user: User[]
  patient: Patient[]
  provider: Provider[]
  user_profile: UserProfile[]
  user_settings: UserSettings[]
  emergency_contact: EmergencyContact[]
  patient_allergy: PatientAllergy[]
  clinic_room: ClinicRoom[]
  slot: Slot[]
  appointment: Appointment[]
  medical_record: MedicalRecord[]
  vital_sign: VitalSign[]
  diagnosis: Diagnosis[]
  record_diagnosis: RecordDiagnosis[]
  medication: Medication[]
  prescription: Prescription[]
  prescription_item: PrescriptionItem[]
  referral: Referral[]
  academic_term: AcademicTerm[]
  student_charge: StudentCharge[]
  audit_log: AuditLog[]
}
