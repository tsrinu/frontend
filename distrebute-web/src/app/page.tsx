'use client'
import { useEffect, useState } from 'react'
import { notifyApi, analyticsApi } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

export default function HomePage() {
  const { token } = useAuth()
  const [inbox, setInbox] = useState<any[] | null>(null)
  const [watchTime, setWatchTime] = useState<any | null>(null)

  useEffect(() => {
    analyticsApi.watchTime().then(setWatchTime).catch(() => {})
    if (token) notifyApi.inbox().then(setInbox).catch(() => {})
  }, [token])

  return (
    <main className="max-w-6xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-2">Welcome to distrebute</h1>
      <p className="text-gray-400 mb-8">
        Hybrid streaming platform — long-form like Netflix, creator UGC like YouTube.
      </p>

      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-4">Today's watch time</h2>
        {watchTime ? (
          <div className="bg-bg2 border border-bg3 rounded-xl p-6">
            <div className="text-4xl font-bold text-brand mb-2">
              {watchTime.totalMinutesWatched} min
            </div>
            <div className="text-sm text-gray-400">across {watchTime.topVideos.length} videos</div>
            <ul className="mt-4 space-y-2">
              {watchTime.topVideos.map((v: any) => (
                <li key={v.videoId} className="flex justify-between text-sm">
                  <span>{v.title}</span><span className="text-gray-500">{v.minutes}m</span>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="text-sm text-gray-500">Loading… (start the analytics-api on :8016)</div>
        )}
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-4">Inbox</h2>
        {!token && (
          <div className="bg-bg2 border border-bg3 rounded-xl p-6 text-sm">
            <a href="/signin" className="text-brand hover:underline">Sign in</a> to see your notifications.
          </div>
        )}
        {token && inbox && (
          <ul className="space-y-3">
            {inbox.map((n: any) => (
              <li key={n.id} className="bg-bg2 border border-bg3 rounded-xl p-4">
                <div className="font-semibold text-sm">{n.title}</div>
                <div className="text-xs text-gray-400 mt-1">{n.body}</div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  )
}
