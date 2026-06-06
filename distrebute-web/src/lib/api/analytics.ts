import { api, APIS } from './base'
export const analyticsApi = {
  emit: (name: string, properties: Record<string, unknown> = {}) =>
    api(APIS.analytics, '/analytics/events',
      { method: 'POST', body: JSON.stringify({ name, properties }) }),
  recent: (limit = 20) => api<unknown[]>(APIS.analytics,
    `/analytics/events/recent?limit=${limit}`, {}, false),
  watchTime: () => api<{ totalMinutesWatched: number; topVideos: unknown[] }>(
    APIS.analytics, '/analytics/watch-time/today', {}, false),
}
