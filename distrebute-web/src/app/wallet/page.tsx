'use client'
import { useEffect, useState } from 'react'
import { billingApi, type Earnings } from '@/lib/api/billing'
import { useAuth } from '@/lib/auth-context'

export default function WalletPage() {
  const { token } = useAuth()
  const [e, setE] = useState<Earnings | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    billingApi.earnings('30d').then(setE).catch((x) => setErr(x.message))
  }, [token])

  if (!token) return (
    <main className="max-w-4xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-4">Creator wallet</h1>
      <p><a href="/signin" className="text-brand hover:underline">Sign in</a> to view earnings.</p>
    </main>
  )

  return (
    <main className="max-w-4xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-2">Creator wallet</h1>
      <p className="text-gray-400 mb-8">Earnings over the last 30 days, by source.</p>
      {err && <div className="text-red-400 text-sm">{err}</div>}
      {e && (
        <>
          <div className="grid grid-cols-4 gap-4 mb-8">
            <Stat label="Total"   value={`$${e.totals.total.toLocaleString()}`} accent />
            <Stat label="Ads"     value={`$${e.totals.ads.toLocaleString()}`} />
            <Stat label="Tips"    value={`$${e.totals.tips.toLocaleString()}`} />
            <Stat label="Members" value={`$${e.totals.members.toLocaleString()}`} />
          </div>
          <h2 className="text-xl font-semibold mb-3">12-month trend</h2>
          <div className="bg-bg2 border border-bg3 rounded-xl p-6 mb-8">
            <div className="flex items-end gap-2 h-32">
              {e.monthlyTrend.map(m => {
                const max = Math.max(...e.monthlyTrend.map(x => x.total))
                return (
                  <div key={m.month} className="flex-1 flex flex-col items-center justify-end gap-1">
                    <div className="w-full rounded-t bg-brand-grad"
                         style={{ height: `${(m.total / max) * 100}%` }} />
                    <span className="text-[10px] text-gray-500">{m.month}</span>
                  </div>
                )
              })}
            </div>
          </div>
          <h2 className="text-xl font-semibold mb-3">Top videos</h2>
          <ul className="space-y-2">
            {e.topVideos.map(v => (
              <li key={v.videoId} className="bg-bg2 border border-bg3 rounded-xl p-4 flex justify-between">
                <div className="text-sm">{v.title}</div>
                <div className="font-semibold">${v.earnings.toLocaleString()}</div>
              </li>
            ))}
          </ul>
        </>
      )}
    </main>
  )
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className={`bg-bg2 border ${accent ? 'border-brand/40' : 'border-bg3'} rounded-xl p-5`}>
      <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</div>
      <div className={`text-2xl font-bold ${accent ? 'text-brand' : ''}`}>{value}</div>
    </div>
  )
}
