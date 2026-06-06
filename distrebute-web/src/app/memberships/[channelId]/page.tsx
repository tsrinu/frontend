'use client'
import { useEffect, useState } from 'react'
import { use } from 'react'
import { billingApi, type Tier } from '@/lib/api/billing'
import { useAuth } from '@/lib/auth-context'

export default function MembershipsPage({ params }: { params: Promise<{ channelId: string }> }) {
  const { channelId } = use(params)
  const { token } = useAuth()
  const [tiers, setTiers] = useState<Tier[]>([])
  const [msg, setMsg] = useState<string | null>(null)

  useEffect(() => { billingApi.tiers(channelId).then(setTiers).catch(() => {}) }, [channelId])

  async function subscribe(tierId: string) {
    if (!token) { window.location.href = '/signin'; return }
    try {
      const r = await billingApi.subscribe(tierId, 'pm_test_card')
      setMsg(`✓ Subscribed (id=${r.id})`)
    } catch (e: any) { setMsg(`✗ ${e.message}`) }
  }

  return (
    <main className="max-w-5xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-2">Support this creator</h1>
      <p className="text-gray-400 mb-6">Channel: {channelId}</p>
      {msg && <div className="mb-4 p-3 bg-bg2 border border-bg3 rounded text-sm">{msg}</div>}
      <div className="grid grid-cols-4 gap-4">
        {tiers.map(t => (
          <div key={t.id} className={`bg-bg2 border ${t.popular ? 'border-brand/50' : 'border-bg3'} rounded-xl p-5`}>
            {t.popular && <div className="text-[10px] text-brand font-bold mb-2">MOST POPULAR</div>}
            <div className="font-bold mb-1">{t.name}</div>
            <div className="text-3xl font-bold mb-3">
              {t.priceCurrency === 'USD' ? '$' : ''}{t.priceAmount}
              <span className="text-sm text-gray-400 font-normal">/{t.billingInterval}</span>
            </div>
            <ul className="text-sm text-gray-300 space-y-1 mb-5 min-h-[120px]">
              {t.perks.map((p, i) => <li key={i}>✓ {p}</li>)}
            </ul>
            <button onClick={() => subscribe(t.id)}
              className={`w-full py-2 rounded-lg text-sm font-bold ${t.popular ? 'bg-brand-grad' : 'bg-bg3 border border-gray-700'}`}>
              Subscribe
            </button>
          </div>
        ))}
      </div>
    </main>
  )
}
