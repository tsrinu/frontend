'use client'
import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { getToken, setToken } from './api/base'

type AuthCtx = {
  token: string | null
  signIn: (t: string) => void
  signOut: () => void
}
const Ctx = createContext<AuthCtx>({ token: null, signIn: () => {}, signOut: () => {} })

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setT] = useState<string | null>(null)
  useEffect(() => { setT(getToken()) }, [])
  return <Ctx.Provider value={{
    token,
    signIn: (t) => { setToken(t); setT(t) },
    signOut: () => { setToken(null); setT(null) },
  }}>{children}</Ctx.Provider>
}
export const useAuth = () => useContext(Ctx)
