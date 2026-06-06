/**
 * Shared fetch wrapper. Reads JWT from localStorage and attaches as Bearer.
 * Throws ApiError on non-2xx. Returns parsed JSON.
 */
export class ApiError extends Error {
  constructor(public status: number, public body: unknown, msg?: string) {
    super(msg ?? `HTTP ${status}`)
  }
}

const TOKEN_KEY = 'distrebute_access_token'

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null) {
  if (typeof window === 'undefined') return
  if (token) window.localStorage.setItem(TOKEN_KEY, token)
  else window.localStorage.removeItem(TOKEN_KEY)
}

export async function api<T = unknown>(
  base: string,
  path: string,
  init: RequestInit = {},
  withAuth = true,
): Promise<T> {
  const headers = new Headers(init.headers ?? {})
  if (!headers.has('Content-Type') && init.body) {
    headers.set('Content-Type', 'application/json')
  }
  const token = withAuth ? getToken() : null
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const res = await fetch(base + path, { ...init, headers })
  let body: unknown
  try {
    body = await res.json()
  } catch {
    body = await res.text().catch(() => null)
  }
  if (!res.ok) throw new ApiError(res.status, body)
  return body as T
}

export const APIS = {
  auth:    process.env.NEXT_PUBLIC_AUTH_API    ?? 'http://127.0.0.1:8001',
  user:    process.env.NEXT_PUBLIC_USER_API    ?? 'http://127.0.0.1:8002',
  billing: process.env.NEXT_PUBLIC_BILLING_API ?? 'http://127.0.0.1:8012',
  live:    process.env.NEXT_PUBLIC_LIVE_API    ?? 'http://127.0.0.1:8013',
  social:  process.env.NEXT_PUBLIC_SOCIAL_API  ?? 'http://127.0.0.1:8014',
  notify:  process.env.NEXT_PUBLIC_NOTIFY_API  ?? 'http://127.0.0.1:8015',
  analytics: process.env.NEXT_PUBLIC_ANALYTICS_API ?? 'http://127.0.0.1:8016',
}
