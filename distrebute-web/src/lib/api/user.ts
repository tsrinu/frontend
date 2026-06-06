import { api, APIS } from './base'

export type User = { id: string; email: string; displayName: string; country: string; language: string }
export type Privacy = { watchHistory: boolean; personalization: boolean; voiceSearchHistory: boolean;
  adPersonalization: boolean; locationForLive: boolean; crashDiagnostics: boolean }
export type Device = { id: string; name: string; type: string; location: string; ipMasked: string;
  lastActiveAt: string; isCurrent: boolean; isFlagged: boolean }
export type Profile = { id: string; name: string; avatarUrl: string; age: number | null;
  isKidProfile: boolean; ageRatingCap: string }

export const userApi = {
  me: () => api<User>(APIS.user, '/users/me'),
  profiles: () => api<Profile[]>(APIS.user, '/users/me/profiles'),
  createProfile: (p: { name: string; isKidProfile: boolean; ageRatingCap?: string }) =>
    api<Profile>(APIS.user, '/users/me/profiles', { method: 'POST', body: JSON.stringify(p) }),
  privacy: () => api<Privacy>(APIS.user, '/users/me/privacy'),
  setPrivacy: (p: Privacy) => api<Privacy>(APIS.user, '/users/me/privacy',
    { method: 'PUT', body: JSON.stringify(p) }),
  setPin: (pin: string) => api<unknown>(APIS.user, '/users/me/pin',
    { method: 'POST', body: JSON.stringify({ pin }) }),
  verifyPin: (pin: string) => api<{ verified: boolean }>(APIS.user, '/users/me/pin/verify',
    { method: 'POST', body: JSON.stringify({ pin }) }),
  devices: () => api<Device[]>(APIS.user, '/users/me/devices'),
  signOutDevice: (id: string) => api<unknown>(APIS.user, `/users/me/devices/${id}`, { method: 'DELETE' }),
  signOutAll: () => api<unknown>(APIS.user, '/users/me/devices/all', { method: 'DELETE' }),
}
