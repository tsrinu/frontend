'use client'
import { useState } from 'react'
import { authApi } from '@/lib/api/auth'
import { useAuth } from '@/lib/auth-context'

export default function SignInPage() {
  const { token, signIn, signOut } = useAuth()
  const [email, setEmail] = useState('tsrinu00@gmail.com')
  const [code, setCode] = useState('')
  const [stage, setStage] = useState<'email'|'code'|'done'>('email')
  const [err, setErr] = useState<string | null>(null)

  async function sendCode() {
    setErr(null)
    try {
      const r = await authApi.emailStart(email)
      // DEV_MODE: the API returns the code so we can autofill it
      if (r._devCode) setCode(r._devCode)
      setStage('code')
    } catch (e: any) { setErr(e.message) }
  }
  async function verify() {
    setErr(null)
    try {
      const t = await authApi.emailVerify(email, code)
      signIn(t.accessToken)
      setStage('done')
    } catch (e: any) { setErr(e.message) }
  }

  if (token) {
    return (
      <main className="max-w-md mx-auto p-8">
        <h1 className="text-2xl font-bold mb-4">You're signed in</h1>
        <p className="text-gray-400 mb-6 text-sm break-all">
          JWT: <code className="text-xs">{token.slice(0, 60)}…</code>
        </p>
        <button onClick={() => { signOut(); setStage('email'); setCode(''); }}
          className="px-5 py-2 bg-bg3 border border-gray-700 rounded-lg hover:bg-bg2">
          Sign out
        </button>
      </main>
    )
  }

  return (
    <main className="max-w-md mx-auto p-8">
      <h1 className="text-3xl font-bold mb-2">Sign in to distrebute</h1>
      <p className="text-gray-400 mb-6">Email OTP. Passkeys/SSO coming next.</p>
      {err && <div className="mb-4 p-3 rounded bg-red-900/30 border border-red-700/50 text-sm">{err}</div>}
      {stage === 'email' && (
        <>
          <label className="block text-sm font-medium mb-1">Email</label>
          <input type="email" value={email} onChange={e => setEmail(e.target.value)}
            className="w-full px-3 py-2 mb-4 bg-bg3 border border-gray-700 rounded-lg" />
          <button onClick={sendCode}
            className="w-full px-4 py-2.5 bg-brand-grad rounded-lg font-semibold">
            Send code
          </button>
        </>
      )}
      {stage === 'code' && (
        <>
          <label className="block text-sm font-medium mb-1">6-digit code (sent to {email})</label>
          <input type="text" value={code} onChange={e => setCode(e.target.value)} maxLength={6}
            className="w-full px-3 py-2 mb-4 bg-bg3 border border-gray-700 rounded-lg text-2xl tracking-widest text-center" />
          <button onClick={verify}
            className="w-full px-4 py-2.5 bg-brand-grad rounded-lg font-semibold">
            Verify
          </button>
        </>
      )}
    </main>
  )
}
