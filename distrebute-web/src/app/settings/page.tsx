'use client'
import { useEffect, useState } from 'react'
import { userApi, type Privacy, type Device } from '@/lib/api/user'
import { useAuth } from '@/lib/auth-context'

export default function SettingsPage() {
  const { token } = useAuth()
  const [privacy, setPrivacy] = useState<Privacy | null>(null)
  const [devices, setDevices] = useState<Device[]>([])
  const [pin, setPin] = useState('')
  const [pinMsg, setPinMsg] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    userApi.privacy().then(setPrivacy).catch(() => {})
    userApi.devices().then(setDevices).catch(() => {})
  }, [token])

  if (!token) return (
    <main className="max-w-4xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-4">Account settings</h1>
      <p><a href="/signin" className="text-brand hover:underline">Sign in</a> to continue.</p>
    </main>
  )

  async function togglePrivacy(key: keyof Privacy) {
    if (!privacy) return
    const next = { ...privacy, [key]: !privacy[key] }
    setPrivacy(next)
    try { await userApi.setPrivacy(next) } catch { /* revert silently */ }
  }

  async function savePin() {
    setPinMsg(null)
    try {
      await userApi.setPin(pin)
      setPinMsg('✓ PIN saved (scrypt-hashed)')
      setPin('')
    } catch (e: any) { setPinMsg(`✗ ${e.message}`) }
  }

  return (
    <main className="max-w-4xl mx-auto p-8 space-y-10">
      <h1 className="text-3xl font-bold">Account settings</h1>

      <section>
        <h2 className="text-xl font-semibold mb-4">Privacy</h2>
        {privacy && (
          <div className="space-y-2">
            {Object.entries(privacy).map(([k, v]) => (
              <label key={k} className="flex items-center justify-between bg-bg2 border border-bg3 rounded-lg p-3 cursor-pointer">
                <span className="text-sm">{k}</span>
                <input type="checkbox" checked={v} onChange={() => togglePrivacy(k as keyof Privacy)}
                  className="w-5 h-5 accent-brand" />
              </label>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-4">Devices ({devices.length})</h2>
        <div className="space-y-2 mb-4">
          {devices.map(d => (
            <div key={d.id} className={`bg-bg2 border ${d.isCurrent ? 'border-green-700/50' : 'border-bg3'} rounded-lg p-3 flex justify-between items-center`}>
              <div>
                <div className="text-sm font-medium">{d.name} {d.isCurrent && <span className="text-xs text-green-500">(this device)</span>}</div>
                <div className="text-xs text-gray-500">{d.location} · {d.ipMasked}</div>
              </div>
              {!d.isCurrent && (
                <button onClick={async () => { await userApi.signOutDevice(d.id); setDevices(await userApi.devices()) }}
                  className="text-xs px-3 py-1.5 bg-bg3 border border-gray-700 rounded">Sign out</button>
              )}
            </div>
          ))}
        </div>
        <button onClick={async () => { await userApi.signOutAll(); setDevices(await userApi.devices()) }}
          className="text-sm px-4 py-2 bg-red-900/30 border border-red-700/50 rounded-lg">
          Sign out of all other devices
        </button>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-4">Household PIN (for kids mode)</h2>
        <div className="flex gap-2">
          <input type="text" maxLength={6} value={pin} onChange={e => setPin(e.target.value)}
            placeholder="4-6 digits" className="w-32 px-3 py-2 bg-bg3 border border-gray-700 rounded-lg text-center text-xl tracking-widest" />
          <button onClick={savePin} className="px-5 py-2 bg-brand-grad rounded-lg font-semibold">Save</button>
        </div>
        {pinMsg && <div className="mt-2 text-sm">{pinMsg}</div>}
      </section>
    </main>
  )
}
