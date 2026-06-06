import { api, APIS } from './base'
export type InboxItem = { id: string; type: string; title: string; body: string;
  linkUrl: string; unread: boolean; createdAt: string }

export const notifyApi = {
  inbox: () => api<InboxItem[]>(APIS.notify, '/notifications/inbox'),
  preferences: () => api<unknown>(APIS.notify, '/notifications/preferences'),
  setPreferences: (p: unknown) => api<unknown>(APIS.notify, '/notifications/preferences',
    { method: 'PUT', body: JSON.stringify(p) }),
}
