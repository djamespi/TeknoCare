import { Hourglass } from 'lucide-react'
import { useStore } from '../data/store'

export function PendingPatientBanner() {
  const { me } = useStore()
  if (me?.account_status !== 'pending') return null
  return (
    <div className="animate-rise mb-8 flex gap-4 rounded-2xl border border-gold/50 bg-gradient-to-r from-gold-100 to-white p-5 text-[#4a3b00] shadow-lg shadow-gold/10 dark:from-gold/10 dark:to-transparent dark:text-gold-100">
      <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-gold text-navy-950"><Hourglass className="size-5" /></span>
      <div>
        <p className="font-semibold">Your account is being verified</p>
        <p className="mt-0.5 text-sm opacity-80">The clinic confirms your school ID before you can book visits. This usually takes less than a day. Walk-ins are always welcome.</p>
      </div>
    </div>
  )
}
