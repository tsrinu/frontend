import { api, APIS } from './base'

export type Tier = { id: string; name: string; priceAmount: number; priceCurrency: string;
  billingInterval: string; perks: string[]; popular: boolean }
export type Earnings = { rangeLabel: string;
  totals: { total: number; ads: number; tips: number; members: number; merch: number };
  monthlyTrend: { month: string; total: number }[];
  topVideos: { videoId: string; title: string; views: number; earnings: number }[] }
export type SuperChat = { id: string; streamId: string; amount: number; currency: string;
  message: string; color: 'blue'|'pink'|'gold'; pinnedSeconds: number }

export const billingApi = {
  tiers: (channelId: string) => api<Tier[]>(APIS.billing,
    `/billing/memberships/tiers/${channelId}`, {}, false),
  subscribe: (tierId: string, paymentMethodId: string) =>
    api<{ id: string; status: string }>(APIS.billing, '/billing/memberships/subscribe',
      { method: 'POST', body: JSON.stringify({ tierId, paymentMethodId }) }),
  superChat: (streamId: string, amount: number, message: string) =>
    api<SuperChat>(APIS.billing, '/billing/super-chat',
      { method: 'POST', body: JSON.stringify({ streamId, amount, currency: 'USD', message }) }),
  giftSubs: (streamId: string, count: 5|25|50|100, tierId: string) =>
    api<{ giftedTo: string[]; totalCharged: number }>(APIS.billing, '/billing/gift-subs',
      { method: 'POST', body: JSON.stringify({ streamId, count, tierId }) }),
  earnings: (range: '30d'|'90d'|'ytd'|'all' = '30d') =>
    api<Earnings>(APIS.billing, `/billing/creator/earnings?range=${range}`),
  pricing: (region: string) => api<{ currency: string; region: string; tiers: Tier[] }>(
    APIS.billing, `/billing/pricing/regional?region=${region}`, {}, false),
}
