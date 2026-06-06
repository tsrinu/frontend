import { api, APIS } from './base'
export type Comment = { id: string; body: string; author: { handle: string; displayName: string;
  verified: boolean }; likes: number; createdAt: string }
export type WatchParty = { roomId: string; videoId: string; inviteUrl: string; participants: unknown[] }

export const socialApi = {
  follow: (channelId: string) => api(APIS.social, `/social/follow/${channelId}`, { method: 'POST' }),
  unfollow: (channelId: string) => api(APIS.social, `/social/follow/${channelId}`, { method: 'DELETE' }),
  comments: (videoId: string) => api<Comment[]>(APIS.social, `/social/comments/${videoId}`, {}, false),
  postComment: (videoId: string, body: string) => api<Comment>(APIS.social,
    `/social/comments/${videoId}`, { method: 'POST', body: JSON.stringify({ body }) }),
  createWatchParty: (videoId: string) => api<WatchParty>(APIS.social, '/social/watch-party',
    { method: 'POST', body: JSON.stringify({ videoId, inviteOnly: false }) }),
}
