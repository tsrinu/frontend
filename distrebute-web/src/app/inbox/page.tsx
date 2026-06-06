'use client'
import { useEffect, useState } from 'react'
import { notifyApi, type InboxItem } from '@/lib/api/notification'
import { useAuth } from '@/lib/auth-context'

export default function InboxPage() {
  const { token } = useAuth()
  const [items, setItems] = useState<InboxItem[]>([])
  useEffect(() => { if (token) notifyApi.inbox().then(setItems).catch(() => {}) }, [token])
  if (!token) return <main className="max-w-3xl mx-auto p-8"><h1 className="text-3xl font-bold mb-4">Inbox</h1><a href="/signin" className="text-brand">Sign in</a></main>
  return (
    <main className="max-w-3xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">Inbox ({items.filter(i => i.unread).length} unread)</h1>
      <ul className="space-y-3">
        {items.map(n => (
          <li key={n.id} className={`p-4 rounded-xl border ${n.unread ? 'border-brand/30 bg-bg2' : 'border-bg3 bg-bg2/50'}`}>
            <div className="font-semibold">{n.title}</div>
            <div className="text-sm text-gray-400 mt-1">{n.body}</div>
            <div className="text-xs text-gray-500 mt-2">{n.type} · {new Date(n.createdAt).toLocaleString()}</div>
          </li>
        ))}
      </ul>
    </main>
  )
}
