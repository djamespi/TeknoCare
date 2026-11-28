import { Shell } from './components/Shell'
import { StoreProvider, useStore } from './data/store'
import { NavProvider, useNav } from './nav'
import Account from './features/account/Page'
import Login from './features/sign-in/Page'
import { Overview } from './features/clinic-overview/Page'
import { People } from './features/people/Page'
import { Charges } from './features/student-charges/Page'
import { Catalog } from './features/clinic-setup/Page'
import { Audit } from './features/audit-log/Page'
import { PatientHome } from './features/patient-home/Page'
import { BookVisit } from './features/book-visit/Page'
import { Appointments } from './features/appointments/Page'
import { Records } from './features/health-records/Page'
import { HealthProfile } from './features/health-profile/Page'
import { Billing } from './features/patient-charges/Page'
import { Today } from './features/provider-queue/Page'
import { Patients } from './features/patient-directory/Page'
import { PatientFile } from './features/patient-file/Page'
import { Schedule } from './features/provider-schedule/Page'
import { Formulary } from './features/formulary/Page'
import { Encounter } from './features/encounter/Page'
import { RecordDetail } from './features/visit-record/Page'

function ProviderPage({ actor, children }: { actor: number; children: React.ReactNode }) {
  const { db } = useStore()
  const eligible = db.provider.some(row => row.provider_id === actor && row.eligible)
  return <Shell>{eligible ? children : <section className="rounded-2xl bg-surface p-8"><h1 className="text-3xl font-bold">Provider activation</h1><p>Your clinic administrator can review your designation and clinical access.</p></section>}</Shell>
}

function Routes() {
  const { me, pending, failed } = useStore()
  const { segments } = useNav()
  if (pending) return <p className="p-8" role="status">Opening TeknoCare…</p>
  if (failed) return <p className="p-8" role="alert">Could not open TeknoCare. <a href="/portal/">Reload the workspace</a>.</p>
  if (!me) return <Login />
  const [head, a, b, c] = segments
  let page
  if (head === 'account') page = <Account />
  else if (me.user_type === 'patient') {
    page = { book: <BookVisit />, appointments: <Appointments />, records: <Records />, health: <HealthProfile />, billing: <Billing /> }[head ?? ''] ?? (head === 'record' && a ? <RecordDetail record_id={Number(a)} backTo="records" backLabel="Health records" /> : <PatientHome />)
  } else if (me.user_type === 'provider') {
    if (head === 'encounter' && a) page = <Encounter key={a} recordId={Number(a)} />
    else if (head === 'patients' && a && b === 'record' && c) page = <RecordDetail record_id={Number(c)} backTo={`patients/${Number(a)}`} backLabel="Patient file" />
    else if (head === 'patients' && a) page = <PatientFile key={a} patientId={Number(a)} />
    else page = { patients: <Patients />, schedule: <Schedule />, formulary: <Formulary /> }[head ?? ''] ?? <Today />
  } else {
    page = { users: <People />, charges: <Charges />, catalog: <Catalog />, audit: <Audit />, schedule: <Schedule /> }[head ?? ''] ?? <Overview />
  }
  if (me.user_type === 'provider' && head !== 'account') {
    return <ProviderPage actor={me.user_id}>{page}</ProviderPage>
  }
  return <Shell>{page}</Shell>
}

export default function App() {
  return (
    <StoreProvider>
      <NavProvider>
        <Routes />
      </NavProvider>
    </StoreProvider>
  )
}
