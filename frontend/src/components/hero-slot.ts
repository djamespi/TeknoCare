import { createContext } from 'react'

// Shell owns the full-bleed hero region; PageHeader portals into it.
export const HeroSlotContext = createContext<HTMLElement | null>(null)
