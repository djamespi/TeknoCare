import {
  useContext, useEffect, useLayoutEffect, useRef, useState, type ButtonHTMLAttributes, type CSSProperties, type InputHTMLAttributes, type ReactNode,
  type SelectHTMLAttributes, type TextareaHTMLAttributes,
} from 'react'
import { createPortal } from 'react-dom'
import { ChevronLeft, X, type LucideIcon } from 'lucide-react'
import { HeroSlotContext } from './hero-slot'

export const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(' ')

type Variant = 'primary' | 'accent' | 'ghost' | 'outline' | 'danger' | 'glass'
export function Button({ variant = 'primary', size = 'md', icon: Icon, className, children, ...rest }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: 'sm' | 'md' | 'lg'; icon?: LucideIcon }) {
  const v = {
    primary: 'sheen bg-gradient-to-b from-navy-700 to-navy text-white shadow-[0_1px_0_rgba(255,255,255,0.15)_inset,0_8px_20px_-8px_rgba(0,40,112,0.6)] hover:shadow-[0_1px_0_rgba(255,255,255,0.15)_inset,0_12px_28px_-8px_rgba(0,40,112,0.7)] hover:-translate-y-px dark:from-navy-700 dark:to-navy-900',
    accent: 'sheen bg-gradient-to-b from-[#ffe04d] to-gold text-navy-950 shadow-[0_1px_0_rgba(255,255,255,0.5)_inset,0_8px_24px_-8px_rgba(253,209,8,0.7)] hover:shadow-[0_1px_0_rgba(255,255,255,0.5)_inset,0_14px_32px_-8px_rgba(253,209,8,0.85)] hover:-translate-y-px',
    ghost: 'text-ink hover:bg-raised',
    outline: 'border border-line bg-surface text-ink shadow-sm shadow-navy/[0.03] hover:border-navy/25 hover:bg-tint',
    danger: 'text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/40',
    glass: 'bg-white/10 text-white ring-1 ring-white/15 backdrop-blur-md hover:bg-white/15',
  }[variant]
  const s = { sm: 'h-8 px-3 text-[13px] gap-1.5 rounded-lg', md: 'h-10 px-4 text-sm gap-2 rounded-xl', lg: 'h-12 px-6 text-[15px] gap-2 rounded-xl' }[size]
  return (
    <button
      className={cx('inline-flex items-center justify-center font-semibold transition-all duration-200 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-45 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gold cursor-pointer whitespace-nowrap', v, s, className)}
      {...rest}
    >
      {Icon && <Icon className={size === 'sm' ? 'size-3.5' : 'size-4'} strokeWidth={2.2} />}
      {children}
    </button>
  )
}

export function Card({ className, children, as: As = 'div', plain }: { className?: string; children: ReactNode; as?: 'div' | 'section' | 'article'; plain?: boolean }) {
  return (
    <As className={cx('rounded-2xl border border-line bg-surface shadow-[0_1px_2px_rgba(0,20,60,0.04),0_8px_24px_-12px_rgba(0,20,60,0.08)] dark:shadow-none', !plain && 'spotlight', className)}>
      {children}
    </As>
  )
}

/** Fades and lifts content in as it scrolls into view. */
export function Reveal({ children, delay = 0, className }: { children: ReactNode; delay?: number; className?: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const [shown, setShown] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (!('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) { setShown(true); return }
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setShown(true); io.disconnect() } }, { rootMargin: '0px 0px -40px 0px' })
    io.observe(el)
    return () => io.disconnect()
  }, [])
  return <div ref={ref} className={cx('reveal', shown && 'is-in', className)} style={{ transitionDelay: `${delay}ms` }}>{children}</div>
}

/** Animated number that counts up on mount. */
export function CountUp({ value, format = (n) => Math.round(n).toLocaleString('en-PH'), duration = 1100 }: { value: number; format?: (n: number) => string; duration?: number }) {
  const [n, setN] = useState(0)
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { setN(value); return }
    let raf = 0
    const t0 = performance.now()
    const tick = (t: number) => {
      const p = Math.min(1, (t - t0) / duration)
      setN(value * (1 - Math.pow(1 - p, 3)))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [value, duration])
  return <>{format(n)}</>
}

export function Sparkline({ data, className, stroke = 'var(--tc-brand)', fill = true }: { data: number[]; className?: string; stroke?: string; fill?: boolean }) {
  if (data.length < 2) return null
  const w = 120, h = 36, pad = 3
  const min = Math.min(...data), max = Math.max(...data)
  const pts = data.map((v, i) => [pad + (i * (w - pad * 2)) / (data.length - 1), h - pad - ((v - min) / (max - min || 1)) * (h - pad * 2)])
  const d = pts.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  const id = `sp${Math.abs(data.reduce((a, b) => a * 31 + b, 7)) % 1e6}`
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className={cx('h-9 w-full overflow-visible', className)} preserveAspectRatio="none" aria-hidden>
      <defs>
        <linearGradient id={id} x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor={stroke} stopOpacity="0.22" /><stop offset="100%" stopColor={stroke} stopOpacity="0" /></linearGradient>
      </defs>
      {fill && <path d={`${d} L${w - pad},${h} L${pad},${h} Z`} fill={`url(#${id})`} />}
      <path d={d} fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" pathLength={1} className="draw" vectorEffect="non-scaling-stroke" />
      <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r="3" fill={stroke} />
    </svg>
  )
}

export function SectionTitle({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="mb-4 flex items-end justify-between gap-4">
      <div>
        <h2 className="text-lg font-semibold">{title}</h2>
        {description && <p className="mt-0.5 text-sm text-muted">{description}</p>}
      </div>
      {action}
    </div>
  )
}

export type HeroStat = { icon: LucideIcon; label: string; value: number; format?: (n: number) => string; hint?: string }

export function GlassStat({ icon: Icon, label, value, format, hint, delay = 0 }: HeroStat & { delay?: number }) {
  return (
    <div className="animate-rise group rounded-2xl bg-white/[0.06] p-4 ring-1 ring-white/10 backdrop-blur-md transition hover:bg-white/[0.09] sm:p-5" style={{ animationDelay: `${150 + delay}ms` }}>
      <div className="flex items-center gap-2 text-[13px] text-white/60"><Icon className="size-4 text-gold" />{label}</div>
      <p className="mt-2 font-display text-[28px] leading-none font-bold text-white"><CountUp value={value} format={format} /></p>
      {hint && <p className="mt-1.5 text-xs text-white/50">{hint}</p>}
    </div>
  )
}

export function PageHeader({ title, description, action, eyebrow, back, stats, children }: {
  title: ReactNode; description?: ReactNode; action?: ReactNode; eyebrow?: ReactNode; back?: { label: string; onClick: () => void }; stats?: HeroStat[]; children?: ReactNode
}) {
  const slot = useContext(HeroSlotContext)
  if (!slot) return null
  return createPortal(
    <div className="relative mx-auto max-w-6xl px-5 pt-8 pb-12 sm:px-8 sm:pt-12 sm:pb-14">
      {back && (
        <button onClick={back.onClick} className="animate-rise mb-6 inline-flex cursor-pointer items-center gap-1 rounded-full bg-white/[0.07] py-1.5 pr-3.5 pl-2 text-[13px] font-medium text-white/75 ring-1 ring-white/10 transition hover:bg-white/[0.12] hover:text-white">
          {back.label}
        </button>
      )}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="min-w-0">
          {eyebrow && <div className="animate-rise mb-4 inline-flex items-center gap-2 rounded-full bg-white/[0.07] px-3 py-1 text-[13px] font-medium text-white/80 ring-1 ring-white/10">{eyebrow}</div>}
          <h1 className="animate-blur-in text-[34px] leading-[1.05] font-bold text-white sm:text-[46px]">{title}</h1>
          {description && <p className="animate-rise mt-3 max-w-2xl text-[15px] leading-relaxed text-white/65 sm:text-base" style={{ animationDelay: '120ms' }}>{description}</p>}
        </div>
        {action && <div className="animate-rise flex shrink-0 flex-wrap gap-2" style={{ animationDelay: '180ms' }}>{action}</div>}
      </div>
      {stats && (
        <div className={cx('mt-9 grid grid-cols-2 gap-3', stats.length >= 4 ? 'lg:grid-cols-4' : 'lg:grid-cols-3')}>
          {stats.map((st, i) => <GlassStat key={st.label} {...st} delay={i * 70} />)}
        </div>
      )}
      {children && <div className="mt-9">{children}</div>}
    </div>,
    slot,
  )
}

const tones = {
  navy: 'bg-navy-50 text-navy dark:bg-navy-700/30 dark:text-navy-100',
  gold: 'bg-gold-100 text-[#6b5500] dark:bg-gold/15 dark:text-gold',
  green: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300',
  red: 'bg-red-50 text-red-700 dark:bg-red-500/15 dark:text-red-300',
  gray: 'bg-raised text-muted',
  amber: 'bg-orange-50 text-orange-700 dark:bg-orange-500/15 dark:text-orange-300',
}
export type Tone = keyof typeof tones
export function Badge({ tone = 'gray', children, dot, pulse }: { tone?: Tone; children: ReactNode; dot?: boolean; pulse?: boolean }) {
  return (
    <span className={cx('inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap', tones[tone])}>
      {dot && (
        <span className="relative flex size-1.5">
          {pulse && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-current opacity-60" />}
          <span className="relative inline-flex size-1.5 rounded-full bg-current" />
        </span>
      )}
      {children}
    </span>
  )
}

export const statusTone: Record<string, Tone> = {
  booked: 'navy', checked_in: 'gold', completed: 'green', canceled: 'gray', no_show: 'red',
  draft: 'gold', finalized: 'green', issued: 'green',
  pending: 'gold', sent: 'navy', accepted: 'green', posted: 'green', voided: 'gray',
  active: 'green', suspended: 'red',
  mild: 'gold', moderate: 'amber', severe: 'red',
}
export const statusLabel: Record<string, string> = {
  booked: 'Upcoming', checked_in: 'Checked in', completed: 'Completed', canceled: 'Canceled', no_show: 'Missed',
  draft: 'In progress', finalized: 'Finalized', issued: 'Issued', pending: 'Pending', sent: 'Sent', accepted: 'Accepted',
  posted: 'Posted to tuition', voided: 'Voided', active: 'Active', suspended: 'Suspended', mild: 'Mild', moderate: 'Moderate', severe: 'Severe',
}
export function Status({ value }: { value: string }) {
  return <Badge tone={statusTone[value] ?? 'gray'} dot pulse={value === 'checked_in' || value === 'pending' || value === 'draft'}>{statusLabel[value] ?? value}</Badge>
}

export function Stat({ icon: Icon, label, value, format, hint, tone = 'navy', trend }: { icon: LucideIcon; label: string; value: number | ReactNode; format?: (n: number) => string; hint?: string; tone?: 'navy' | 'gold'; trend?: number[] }) {
  return (
    <Card className="group overflow-hidden p-5 transition duration-300 hover:-translate-y-0.5">
      <div className="flex items-start justify-between">
        <div className={cx('grid size-11 place-items-center rounded-xl transition duration-300 group-hover:scale-110 group-hover:-rotate-3', tone === 'gold' ? 'bg-gradient-to-br from-[#ffe04d] to-gold text-navy-950 shadow-lg shadow-gold/30' : 'bg-gradient-to-br from-navy to-navy-700 text-gold shadow-lg shadow-navy/20')}>
          <Icon className="size-5" />
        </div>
        {trend && <div className="w-20"><Sparkline data={trend} /></div>}
      </div>
      <p className="mt-4 text-[13px] font-medium text-muted">{label}</p>
      <p className="mt-0.5 font-display text-[26px] leading-tight font-bold">{typeof value === 'number' ? <CountUp value={value} format={format} /> : value}</p>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </Card>
  )
}

export function Field({ label, hint, children, className }: { label: string; hint?: string; children: ReactNode; className?: string }) {
  return (
    <label className={cx('block', className)}>
      <span className="mb-1.5 block text-[13px] font-semibold text-ink">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-muted">{hint}</span>}
    </label>
  )
}
const control = 'w-full rounded-xl border border-line bg-surface px-3.5 text-sm text-ink placeholder:text-muted/70 transition focus:border-navy focus:ring-4 focus:ring-navy/10 focus:outline-none dark:focus:border-navy-100 dark:focus:ring-navy-100/10 disabled:opacity-60'
export function Input(p: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...p} className={cx(control, 'h-11', p.className)} />
}
export function Textarea(p: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea rows={3} {...p} className={cx(control, 'resize-y py-2.5 leading-relaxed', p.className)} />
}
export function Select(p: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...p} className={cx(control, 'h-11 cursor-pointer pr-8', p.className)} />
}

export function Toggle({ checked, onChange, label, description }: { checked: boolean; onChange: (v: boolean) => void; label: string; description?: string }) {
  return (
    <button type="button" role="switch" aria-checked={checked} onClick={() => onChange(!checked)} className="flex w-full cursor-pointer items-center justify-between gap-6 py-3 text-left">
      <span>
        <span className="block text-sm font-semibold">{label}</span>
        {description && <span className="block text-[13px] text-muted">{description}</span>}
      </span>
      <span className={cx('relative h-6 w-11 shrink-0 rounded-full transition-colors', checked ? 'bg-navy dark:bg-gold' : 'bg-line')}>
        <span className={cx('absolute top-0.5 size-5 rounded-full bg-white shadow transition-all', checked ? 'left-[22px]' : 'left-0.5')} />
      </span>
    </button>
  )
}

export function Modal({ open, onClose, title, description, children, wide }: { open: boolean; onClose: () => void; title: string; description?: string; children: ReactNode; wide?: boolean }) {
  useEffect(() => {
    if (!open) return
    const k = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', k)
    return () => window.removeEventListener('keydown', k)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-6" role="dialog" aria-modal="true" aria-label={title}>
      <div className="absolute inset-0 bg-navy-950/50 backdrop-blur-sm" onClick={onClose} />
      <div className={cx('animate-rise relative max-h-[92vh] w-full overflow-y-auto rounded-t-3xl border border-line bg-surface p-6 shadow-2xl sm:rounded-3xl sm:p-8', wide ? 'sm:max-w-2xl' : 'sm:max-w-lg')}>
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold">{title}</h2>
            {description && <p className="mt-1 text-sm text-muted">{description}</p>}
          </div>
          <button onClick={onClose} aria-label="Close" className="-mr-2 -mt-1 cursor-pointer rounded-full p-2 text-muted hover:bg-raised hover:text-ink">
            <X className="size-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

export function Empty({ icon: Icon, title, text, action }: { icon: LucideIcon; title: string; text?: string; action?: ReactNode }) {
  return (
    <div className="relative flex flex-col items-center overflow-hidden px-6 py-14 text-center">
      <div className="dot-grid pointer-events-none absolute inset-0 [mask-image:radial-gradient(circle_at_center,#000,transparent_65%)]" />
      <div className="relative mb-4 grid size-14 place-items-center rounded-2xl bg-gradient-to-br from-navy to-navy-700 text-gold shadow-lg shadow-navy/25">
        <Icon className="size-6" />
      </div>
      <p className="relative font-display text-lg font-semibold">{title}</p>
      {text && <p className="relative mt-1 max-w-sm text-sm text-muted">{text}</p>}
      {action && <div className="relative mt-5">{action}</div>}
    </div>
  )
}

export function Avatar({ name, size = 'md', tone = 'navy', className }: { name: string; size?: 'sm' | 'md' | 'lg'; tone?: 'navy' | 'gold'; className?: string }) {
  const initials = name.split(' ').filter((w) => /^[A-Z]/.test(w) && !/^(Dr|Nurse)\.?$/.test(w)).slice(0, 2).map((w) => w[0]).join('')
  const s = { sm: 'size-8 text-xs', md: 'size-10 text-sm', lg: 'size-14 text-lg' }[size]
  return <span className={cx('grid shrink-0 place-items-center rounded-full font-display font-semibold', tone === 'gold' ? 'bg-gold text-navy-950' : 'bg-navy text-gold', s, className)}>{initials}</span>
}

export function Tabs<T extends string>({ value, onChange, items }: { value: T; onChange: (v: T) => void; items: { value: T; label: string; count?: number }[] }) {
  const wrap = useRef<HTMLDivElement>(null)
  const [pill, setPill] = useState<CSSProperties>({ opacity: 0 })
  useLayoutEffect(() => {
    const tabs = wrap.current?.querySelectorAll<HTMLButtonElement>('[data-value]') ?? []
    const el = Array.from(tabs).find(tab => tab.dataset.value === value)
    if (el) setPill({ left: el.offsetLeft, top: el.offsetTop, width: el.offsetWidth, height: el.offsetHeight, opacity: 1 })
  }, [value, items.length])
  return (
    <div ref={wrap} role="tablist" className="relative inline-flex max-w-full flex-wrap gap-1 rounded-xl bg-raised p-1 ring-1 ring-line/60">
      <span aria-hidden className="absolute rounded-lg bg-surface shadow-[0_1px_3px_rgba(0,20,60,0.12)] transition-all duration-300 ease-[cubic-bezier(0.3,0.7,0.2,1)] dark:bg-navy-700" style={pill} />
      {items.map((i) => (
        <button
          key={i.value}
          data-value={i.value}
          role="tab"
          aria-selected={value === i.value}
          onClick={() => onChange(i.value)}
          className={cx('relative flex cursor-pointer items-center gap-2 rounded-lg px-3.5 py-1.5 text-sm font-semibold transition-colors', value === i.value ? 'text-ink' : 'text-muted hover:text-ink')}
        >
          {i.label}
          {i.count != null && <span className={cx('rounded-full px-1.5 text-[11px] transition-colors', value === i.value ? 'bg-navy text-white dark:bg-gold dark:text-navy-950' : 'bg-line text-muted')}>{i.count}</span>}
        </button>
      ))}
    </div>
  )
}

export function Toast({ message, onDone }: { message: string | null; onDone: () => void }) {
  useEffect(() => {
    if (!message) return
    const t = setTimeout(onDone, 3200)
    return () => clearTimeout(t)
  }, [message, onDone])
  if (!message) return null
  return (
    <div className="animate-rise fixed bottom-6 left-1/2 z-[60] -translate-x-1/2 rounded-2xl bg-navy-950 px-5 py-3 text-sm font-medium text-white shadow-2xl ring-1 ring-white/10" role="status">
      <span className="mr-2 inline-block size-2 rounded-full bg-gold align-middle" />
      {message}
    </div>
  )
}

export function Logo({ light }: { light?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <span className="relative grid size-9 place-items-center rounded-xl bg-gold">
        <svg viewBox="0 0 24 24" className="size-5 text-navy" fill="currentColor" aria-hidden>
          <path d="M9.5 3h5a1 1 0 0 1 1 1v4.5H20a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1h-4.5V20a1 1 0 0 1-1 1h-5a1 1 0 0 1-1-1v-4.5H4a1 1 0 0 1-1-1v-5a1 1 0 0 1 1-1h4.5V4a1 1 0 0 1 1-1Z" />
        </svg>
      </span>
      <span className={cx('font-display text-[19px] font-bold tracking-tight', light ? 'text-white' : 'text-ink')}>
        Tekno<span className={light ? 'text-gold' : 'text-brand'}>Care</span>
      </span>
    </span>
  )
}
