import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { Toast } from './components/ui'
import { DomainError, useStore } from './data/store'

type Nav = {
  route: string
  segments: string[]
  go: (r: string) => void
  toast: (m: string) => void
  // Runs an action, surfacing domain errors as toasts instead of crashing.
  run: (fn: () => unknown, success?: string) => Promise<boolean>
}
const Ctx = createContext<Nav | null>(null)

const read = () => window.location.hash.replace(/^#\/?/, '')

export function NavProvider({ children }: { children: ReactNode }) {
  const { saving } = useStore()
  const [route, setRoute] = useState(read)
  const [msg, setMsg] = useState<string | null>(null)
  useEffect(() => {
    const h = () => setRoute(read())
    window.addEventListener('hashchange', h)
    return () => window.removeEventListener('hashchange', h)
  }, [])
  const go = useCallback((r: string) => {
    window.location.hash = '/' + r
    setRoute(r)
    window.scrollTo({ top: 0 })
  }, [])
  const toast = useCallback((m: string) => setMsg(m), [])
  const run = useCallback(async (fn: () => unknown, success?: string) => {
    try {
      await fn()
      if (success) setMsg(success)
      return true
    } catch (e) {
      setMsg(e instanceof DomainError ? e.message : 'Something went wrong. Please try again.')
      if (!(e instanceof DomainError)) console.error(e)
      return false
    }
  }, [])
  const clear = useCallback(() => setMsg(null), [])
  return (
    <Ctx.Provider value={{ route, segments: route.split('/').filter(Boolean), go, toast, run }}>
      {children}
      {saving && <p role="status" className="pointer-events-none fixed right-4 bottom-20 z-[60] rounded-xl bg-navy-950 px-4 py-2 text-sm font-medium text-white shadow-lg">Saving changes…</p>}
      <Toast message={msg} onDone={clear} />
    </Ctx.Provider>
  )
}

export function useNav() {
  const n = useContext(Ctx)
  if (!n) throw new Error('useNav outside provider')
  return n
}
