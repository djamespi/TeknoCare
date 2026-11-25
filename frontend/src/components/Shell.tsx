import { clinicStatus } from '../data/format'
import { useEffect, useState, type ReactNode } from 'react'
import {
  CalendarCheck, CalendarPlus, CalendarRange, ChevronDown, ClipboardList, FileHeart, HeartPulse, House, LayoutDashboard, Library, LogOut,
  Clock, Mail, MapPin, Menu, Moon, Phone, Receipt, ShieldCheck, ScrollText, Settings2, Stethoscope, Sun, Users, Wallet, X, type LucideIcon,
} from 'lucide-react'
import { useLookups, useStore } from '../data/store'
import { useNav } from '../nav'
import { HeroSlotContext } from './hero-slot'
import { Avatar, Logo, cx } from './ui'

type Item = { to: string; label: string; icon: LucideIcon; badge?: number }

export function useNavItems(): Item[] {
  const { me, db } = useStore()
  if (!me) return []
  if (me.user_type === 'patient') {
    const upcoming = db.appointment.filter((a) => a.patient_id === me.user_id && a.status === 'booked').length
    return [
      { to: 'home', label: 'Home', icon: House },
      { to: 'book', label: 'Book a visit', icon: CalendarPlus },
      { to: 'appointments', label: 'Appointments', icon: CalendarCheck, badge: upcoming || undefined },
      { to: 'records', label: 'Records', icon: FileHeart },
      { to: 'health', label: 'Health profile', icon: HeartPulse },
      { to: 'billing', label: 'Charges', icon: Wallet },
    ]
  }
  if (me.user_type === 'provider') {
    return [
      { to: 'today', label: 'Today', icon: Stethoscope },
      { to: 'patients', label: 'Patients', icon: Users },
      { to: 'schedule', label: 'Schedule', icon: CalendarRange },
      { to: 'formulary', label: 'Formulary', icon: Library },
    ]
  }
  const charges = db.student_charge.filter((c) => c.status === 'pending').length
  return [
    { to: 'overview', label: 'Overview', icon: LayoutDashboard },
    { to: 'users', label: 'People', icon: Users },
    { to: 'charges', label: 'Charges', icon: Receipt, badge: charges || undefined },
    { to: 'schedule', label: 'Schedules', icon: CalendarRange },
    { to: 'catalog', label: 'Clinic setup', icon: ClipboardList },
    { to: 'audit', label: 'Audit log', icon: ScrollText },
  ]
}

function isActive(current: string | undefined, to: string) {
  return current === to || (to === 'records' && current === 'record') || (to === 'today' && current === 'encounter')
}

export function Shell({ children }: { children: ReactNode }) {
  const { me, db, actions } = useStore()
  const { name } = useLookups()
  const { go, segments, route, run } = useNav()
  const items = useNavItems()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [userOpen, setUserOpen] = useState(false)
  const [slot, setSlot] = useState<HTMLElement | null>(null)
  const [scrolled, setScrolled] = useState(false)
  const current = segments[0]

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    // Feeds the cursor position to the hovered .spotlight card.
    const onMove = (e: PointerEvent) => {
      const el = (e.target as Element | null)?.closest?.('.spotlight') as HTMLElement | null
      if (!el) return
      const r = el.getBoundingClientRect()
      el.style.setProperty('--mx', `${e.clientX - r.left}px`)
      el.style.setProperty('--my', `${e.clientY - r.top}px`)
    }
    window.addEventListener('pointermove', onMove, { passive: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('pointermove', onMove)
    }
  }, [])

  // Close menus whenever the route changes.
  useEffect(() => {
    setMobileOpen(false)
    setUserOpen(false)
  }, [route])

  if (!me) return null
  const settings = db.user_settings.find((s) => s.user_id === me.user_id)
  const dark = settings?.dark_mode ?? false
  const provider = db.provider.find((p) => p.provider_id === me.user_id)
  const patient = db.patient.find((p) => p.patient_id === me.user_id)
  const role = me.user_type === 'admin' ? 'Clinic administrator' : provider ? provider.specialization ?? 'Provider' : `${patient?.affiliation ? patient.affiliation[0].toUpperCase() + patient.affiliation.slice(1) : 'Patient'} · ${me.school_id}`
  const home = items[0]?.to ?? ''

  return (
    <div className={cx('min-h-screen bg-canvas text-ink', dark && 'dark')}>
      <a href="#main-content" onClick={(event) => { event.preventDefault(); document.getElementById('main-content')?.focus() }} className="sr-only z-50 focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:bg-gold focus:p-3">Skip to main content</a>
      <header className={cx('sticky top-0 z-30 text-white transition-[background-color,box-shadow,backdrop-filter] duration-300', scrolled || mobileOpen ? 'bg-navy/85 shadow-[0_10px_40px_-12px_rgba(0,19,58,0.55)] backdrop-blur-xl backdrop-saturate-150 dark:bg-navy-950/85' : 'bg-transparent')}>
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-2 px-5 sm:px-8">
          <button onClick={() => go(home)} className="mr-4 shrink-0 cursor-pointer rounded-xl focus-visible:outline-2 focus-visible:outline-gold" aria-label="TeknoCare home">
            <Logo light />
          </button>

          <nav className="hidden h-full items-stretch gap-0.5 lg:flex" aria-label="Main">
            {items.map(({ to, label, icon: Icon, badge }) => {
              const active = isActive(current, to)
              return (
                <button
                  key={to}
                  onClick={() => go(to)}
                  aria-current={active ? 'page' : undefined}
                  className={cx(
                    'group relative flex cursor-pointer items-center gap-2 px-3 text-[14px] font-medium transition-colors',
                    active ? 'text-white' : 'text-white/65 hover:text-white',
                  )}
                >
                  <span className={cx('flex items-center gap-2 rounded-lg px-1 py-1.5 transition', !active && 'group-hover:bg-white/[0.06]')}>
                    <Icon className={cx('hidden size-4 xl:block', active ? 'text-gold' : '')} strokeWidth={2} />
                    {label}
                    {badge != null && <span className="rounded-full bg-gold px-1.5 py-px text-[11px] leading-4 font-bold text-navy-950">{badge}</span>}
                  </span>
                  <span className={cx('absolute inset-x-3 bottom-0 h-[3px] rounded-t-full bg-gold transition-opacity', active ? 'opacity-100' : 'opacity-0')} />
                </button>
              )
            })}
          </nav>

          <div className="ml-auto flex items-center gap-1">
            <button
              aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
              onClick={() => actions.updateSettings(me.user_id, { dark_mode: !dark })}
              className="grid size-10 cursor-pointer place-items-center rounded-full text-white/70 transition hover:bg-white/10 hover:text-white"
            >
              {dark ? <Sun className="size-[18px]" /> : <Moon className="size-[18px]" />}
            </button>

            <div className="relative hidden lg:block">
              <button
                onClick={() => setUserOpen((v) => !v)}
                aria-expanded={userOpen}
                aria-haspopup="menu"
                className="flex cursor-pointer items-center gap-2 rounded-full py-1 pr-2 pl-1 transition hover:bg-white/10"
              >
                <Avatar name={name(me.user_id)} size="sm" tone="gold" />
                <ChevronDown className={cx('size-4 text-white/70 transition', userOpen && 'rotate-180')} />
              </button>
              {userOpen && (
                <>
                  <div className="fixed inset-0 z-0" onClick={() => setUserOpen(false)} />
                  <div role="menu" className="animate-rise absolute top-12 right-0 z-10 w-72 overflow-hidden rounded-2xl border border-line bg-surface text-ink shadow-2xl shadow-navy-950/20">
                    <div className="flex items-center gap-3 border-b border-line p-4">
                      <Avatar name={name(me.user_id)} />
                      <div className="min-w-0">
                        <p className="truncate font-semibold">{name(me.user_id)}</p>
                        <p className="truncate text-xs text-muted">{role}</p>
                      </div>
                    </div>
                    <div className="p-2">
                      <button role="menuitem" onClick={() => go('account')} className="flex w-full cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium hover:bg-raised">
                        <Settings2 className="size-4 text-muted" /> Account & settings
                      </button>
                      <button role="menuitem" onClick={() => run(async () => { await actions.logout(); go('') })} className="flex w-full cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium hover:bg-raised">
                        <LogOut className="size-4 text-muted" /> Sign out
                      </button>
                    </div>

                  </div>
                </>
              )}
            </div>

            <button
              aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={mobileOpen}
              onClick={() => setMobileOpen((v) => !v)}
              className="grid size-10 cursor-pointer place-items-center rounded-full text-white transition hover:bg-white/10 lg:hidden"
            >
              {mobileOpen ? <X className="size-5" /> : <Menu className="size-5" />}
            </button>
          </div>
        </div>

        {mobileOpen && (
          <div className="animate-rise border-t border-white/10 lg:hidden">
            <div className="mx-auto max-w-6xl px-5 pt-3 pb-5 sm:px-8">
              <div className="mb-3 flex items-center gap-3 rounded-2xl bg-white/[0.06] p-3">
                <Avatar name={name(me.user_id)} size="sm" tone="gold" />
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold">{name(me.user_id)}</p>
                  <p className="truncate text-xs text-white/60">{role}</p>
                </div>
              </div>
              <nav className="grid gap-1 sm:grid-cols-2" aria-label="Main">
                {items.map(({ to, label, icon: Icon, badge }) => {
                  const active = isActive(current, to)
                  return (
                    <button key={to} onClick={() => go(to)} className={cx('flex cursor-pointer items-center gap-3 rounded-xl px-3 py-3 text-[15px] font-medium transition', active ? 'bg-white/10 text-white' : 'text-white/70 hover:bg-white/5 hover:text-white')}>
                      <Icon className={cx('size-[18px]', active && 'text-gold')} />
                      <span className="flex-1 text-left">{label}</span>
                      {badge != null && <span className="rounded-full bg-gold px-2 py-px text-[11px] font-bold text-navy-950">{badge}</span>}
                    </button>
                  )
                })}
              </nav>
              <div className="mt-3 grid grid-cols-2 gap-1 border-t border-white/10 pt-3">
                <button onClick={() => go('account')} className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-3 text-[15px] font-medium text-white/70 hover:bg-white/5 hover:text-white"><Settings2 className="size-[18px]" /> Account</button>
                <button onClick={() => run(async () => { await actions.logout(); go('') })} className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-3 text-[15px] font-medium text-white/70 hover:bg-white/5 hover:text-white"><LogOut className="size-[18px]" /> Sign out</button>
              </div>
            </div>
          </div>
        )}
      </header>

      <div className="relative -mt-16 overflow-hidden bg-navy pt-16 text-white dark:bg-navy-950">
        <HeroBackdrop />
        <div ref={setSlot} key={route} className="relative" />
      </div>

      <HeroSlotContext.Provider value={slot}>
        <main id="main-content" tabIndex={-1} key={route} className="animate-rise mx-auto min-h-[45vh] max-w-6xl px-5 pt-8 pb-6 sm:px-8 sm:pt-10">{children}</main>
      </HeroSlotContext.Provider>

      <Footer />
    </div>
  )
}

function HeroBackdrop() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0">
      <div className="aurora-a absolute -top-48 right-[-8%] size-[560px] rounded-full bg-gold/20 blur-[120px]" />
      <div className="aurora-b absolute -bottom-64 left-[-12%] size-[640px] rounded-full bg-[#2f6bff]/25 blur-[130px]" />
      <div className="absolute top-0 left-[35%] size-[340px] rounded-full bg-navy-700/70 blur-[110px]" />
      <div className="hero-grid absolute inset-0" />
      <svg viewBox="0 0 24 24" className="animate-float absolute top-16 right-[-60px] hidden size-[380px] text-white/[0.045] md:block" fill="none" stroke="currentColor" strokeWidth="0.35">
        <path d="M9.5 3h5a1 1 0 0 1 1 1v4.5H20a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1h-4.5V20a1 1 0 0 1-1 1h-5a1 1 0 0 1-1-1v-4.5H4a1 1 0 0 1-1-1v-5a1 1 0 0 1 1-1h4.5V4a1 1 0 0 1 1-1Z" />
      </svg>
      <div className="noise absolute inset-0" />
      <div className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-gold/60 to-transparent" />
    </div>
  )
}

function Footer() {
  const { demo } = useStore()
  return demo ? <SampleFooter /> : <ClinicFooter />
}

function ClinicFooter() {
  return (
    <footer className="relative mt-20 overflow-hidden bg-navy-950 text-white">
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="absolute -top-40 left-1/2 h-72 w-[70%] -translate-x-1/2 rounded-full bg-navy-700/40 blur-[100px]" />
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-gold/50 to-transparent" />
        <div className="noise absolute inset-0" />
      </div>
      <div className="relative mx-auto grid max-w-6xl gap-10 px-5 py-14 sm:px-8 md:grid-cols-[1.5fr_1fr_1fr_1fr]">
        <div>
          <Logo light />
          <p className="mt-4 max-w-xs text-sm leading-relaxed text-white/70">CIT-University clinic school prototype for students, faculty and staff.</p>
        </div>
        <div>
          <p className="mb-4 flex items-center gap-2 font-display font-semibold"><Clock className="size-4 text-gold" />Clinic visits</p>
          <p className="text-sm leading-relaxed text-white/70">Available times are displayed in Manila time.</p>
        </div>
        <div>
          <p className="mb-4 flex items-center gap-2 font-display font-semibold"><MapPin className="size-4 text-gold" />Campus</p>
          <p className="text-sm leading-relaxed text-white/70">CIT-University, Cebu City</p>
        </div>
        <div>
          <p className="mb-4 flex items-center gap-2 font-display font-semibold"><ShieldCheck className="size-4 text-gold" />Account help</p>
          <p className="text-sm leading-relaxed text-white/70">Contact the clinic administrator for assistance.</p>
        </div>
      </div>
      <div className="relative border-t border-white/10">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-5 py-5 text-xs text-white/45 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <span>TeknoCare · CIT-University clinic</span>
          <span className="flex items-center gap-1.5"><ShieldCheck className="size-3.5" />Use fictional data only</span>
        </div>
      </div>
    </footer>
  )
}

function SampleFooter() {
  const status = clinicStatus()
  return (
    <footer className="relative mt-20 overflow-hidden bg-navy-950 text-white">
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="absolute -top-40 left-1/2 h-72 w-[70%] -translate-x-1/2 rounded-full bg-navy-700/40 blur-[100px]" />
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-gold/50 to-transparent" />
        <div className="noise absolute inset-0" />
      </div>
      <div className="relative mx-auto grid max-w-6xl gap-10 px-5 py-14 sm:px-8 md:grid-cols-[1.5fr_1fr_1fr_1fr]">
        <div>
          <Logo light />
          <p className="mt-4 max-w-xs text-sm leading-relaxed text-white/55">The Health Services Center of Cebu Institute of Technology – University, caring for students, faculty and staff since day one.</p>
          <span className={cx('mt-5 inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ring-1', status.open ? 'bg-emerald-400/10 text-emerald-300 ring-emerald-400/20' : 'bg-white/5 text-white/60 ring-white/10')}>
            <span className="relative flex size-2">
              {status.open && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-70" />}
              <span className={cx('relative inline-flex size-2 rounded-full', status.open ? 'bg-emerald-400' : 'bg-white/40')} />
            </span>
            {status.label}
          </span>
        </div>
        <div>
          <p className="mb-4 flex items-center gap-2 font-display font-semibold"><Clock className="size-4 text-gold" />Sample clinic hours</p>
          <ul className="space-y-2 text-sm text-white/60">
            <li className="flex justify-between gap-4"><span>Mon – Fri</span><span className="text-white/80">8:00 AM – 5:00 PM</span></li>
            <li className="flex justify-between gap-4"><span>Saturday</span><span className="text-white/80">8:00 AM – 12:00 PM</span></li>
            <li className="flex justify-between gap-4"><span>Sunday</span><span className="text-white/80">Closed</span></li>
          </ul>
        </div>
        <div>
          <p className="mb-4 flex items-center gap-2 font-display font-semibold"><MapPin className="size-4 text-gold" />Find us</p>
          <p className="text-sm leading-relaxed text-white/60">Health Services Center<br />Main Campus, N. Bacalso Avenue<br />Cebu City, 6000</p>
        </div>
        <div>
          <p className="mb-4 flex items-center gap-2 font-display font-semibold"><Phone className="size-4 text-gold" />Get in touch</p>
          <ul className="space-y-2 text-sm text-white/60">
            <li>Contact the clinic administrator for support.</li>
          </ul>
        </div>
      </div>
      <div className="relative border-t border-white/10">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-5 py-5 text-xs text-white/45 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <span>© {new Date().getFullYear()} Cebu Institute of Technology – University · TeknoCare</span>
          <span className="flex items-center gap-1.5"><ShieldCheck className="size-3.5" />Fictional clinic workflow</span>
        </div>
      </div>
    </footer>
  )
}
