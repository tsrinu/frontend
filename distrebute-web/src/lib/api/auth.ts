import { api, APIS, setToken } from './base'

export type TokenPair = { accessToken: string; refreshToken: string; expiresIn: number }

export const authApi = {
  emailStart: (email: string) =>
    api<{ status: string; _devCode?: string }>(APIS.auth, '/auth/email/start',
      { method: 'POST', body: JSON.stringify({ email }) }, false),

  emailVerify: async (email: string, code: string) => {
    const t = await api<TokenPair>(APIS.auth, '/auth/email/verify',
      { method: 'POST', body: JSON.stringify({ email, code }) }, false)
    setToken(t.accessToken)
    return t
  },

  ssoGoogle: async (idToken: string, email?: string) => {
    const t = await api<TokenPair>(APIS.auth, '/auth/sso/google',
      { method: 'POST', body: JSON.stringify({ idToken, email }) }, false)
    setToken(t.accessToken)
    return t
  },

  securityHealth: () =>
    api<{ score: number; grade: string; checks: { key: string; label: string; status: string }[] }>(
      APIS.auth, '/auth/security/health'),

  events: () =>
    api<Array<{ id: string; type: string; at: string; device: string; location: string; flagged: boolean }>>(
      APIS.auth, '/auth/events?limit=10'),

  twoFASetup: () =>
    api<{ qrPngBase64: string; secret: string; recoveryCodes: string[] }>(
      APIS.auth, '/auth/2fa/setup', { method: 'POST' }),

  twoFAVerify: (code: string) =>
    api<{ status: string }>(APIS.auth, '/auth/2fa/verify',
      { method: 'POST', body: JSON.stringify({ code }) }),

  signOut: () => setToken(null),
}
