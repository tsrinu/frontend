import { api, APIS } from './base'
export type Stream = { id: string; channelId: string; title: string; viewerCount: number;
  tags: string[]; status: string }
export type Poll = { id: string; question: string;
  options: { text: string; votes: number; percent: number }[]; endsAt: string }

export const liveApi = {
  stream: (id: string) => api<Stream>(APIS.live, `/live/streams/${id}`, {}, false),
  chatTicket: (id: string) => api<{ wsUrl: string; token: string }>(APIS.live, `/live/streams/${id}/chat`, {}, false),
  createPoll: (streamId: string, question: string, options: string[]) =>
    api<Poll>(APIS.live, `/live/streams/${streamId}/poll`,
      { method: 'POST', body: JSON.stringify({ question, options, durationSec: 90 }) }),
  vote: (streamId: string, pollId: string, optionIndex: number) =>
    api(APIS.live, `/live/streams/${streamId}/poll/${pollId}/vote`,
      { method: 'POST', body: JSON.stringify({ optionIndex }) }),
}
