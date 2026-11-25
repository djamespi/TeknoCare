import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { Toast } from './components/ui'
import { DomainError } from './data/store'

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
      <Toast message={msg} onDone={clear} />
    </Ctx.Provider>
  )
}

export function useNav() {
  const n = useContext(Ctx)
  if (!n) throw new Error('useNav outside provider')
  return n
}
