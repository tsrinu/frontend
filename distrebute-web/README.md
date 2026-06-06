# distrebute-web — Next.js 15 frontend

Real customer-facing UI that calls the 7 backend APIs.

## Quick start

```cmd
cd C:\Users\slua_187012ca5b4f\Documents\API\distrebute-web

REM 1. Install
npm install

REM 2. Copy env (defaults point at localhost APIs)
copy .env.local.example .env.local

REM 3. Make sure backend is running (in another window)
cd ..
double-click run-all-apis.bat

REM 4. Start dev server
cd distrebute-web
npm run dev

REM Open http://localhost:3000
```

## What's in this scaffold

| Page | Backend API | UI template |
|---|---|---|
| `/` (home) | analytics-api watch-time + notify-api inbox | #01 |
| `/signin` | auth-api email OTP | #18 |
| `/wallet` | billing-api creator earnings | #09 |
| `/memberships/[ch]` | billing-api tiers + subscribe | #10 |
| `/settings` | user-api privacy + devices + PIN | #19, #20, #21 |
| `/inbox` | notification-api inbox | #08 |

Plus skeletons for `/creator/[handle]`, `/watch/[id]`, `/live/[id]`, `/search`, `/shorts` — easy to fill in following the same pattern.

## File structure

```
distrebute-web/
├── package.json                 Next.js 15 + React 19 + TypeScript + Tailwind
├── next.config.js
├── tsconfig.json
├── tailwind.config.ts           Brand colors from the mockups
├── Dockerfile                   Multi-stage prod build
├── .env.local.example
└── src/
    ├── app/
    │   ├── layout.tsx           NavBar + AuthProvider
    │   ├── globals.css
    │   ├── page.tsx             Home
    │   ├── signin/page.tsx      Email OTP sign-in
    │   ├── wallet/page.tsx      Creator earnings dashboard
    │   ├── settings/page.tsx    Privacy + devices + PIN
    │   ├── memberships/[channelId]/page.tsx
    │   └── inbox/page.tsx
    ├── lib/
    │   ├── auth-context.tsx    JWT in localStorage; React context
    │   └── api/
    │       ├── base.ts          fetch wrapper + token mgmt
    │       ├── auth.ts          calls auth-api (sign-in, 2FA, security health)
    │       ├── user.ts          calls user-api (profiles, devices, PIN, privacy)
    │       ├── billing.ts       calls billing-api (tiers, super-chat, gift-subs, earnings)
    │       ├── social.ts        calls social-api
    │       ├── live.ts          calls live-api
    │       ├── notification.ts  calls notification-api
    │       ├── analytics.ts     calls analytics-api
    │       └── index.ts         barrel re-export
```

## Build for production

```cmd
npm run build
npm start
```

Or via Docker:

```cmd
docker build -t distrebute-web .
docker run -p 3000:3000 -e NEXT_PUBLIC_AUTH_API=https://api.distrebute.com distrebute-web
```

## Regenerate the TypeScript client when openapi.yaml changes

```cmd
npm run gen:api
REM Produces src/lib/api/openapi-types.ts — fully typed responses + request bodies
```

## What's NOT in this scaffold (deferred)

- shadcn/ui components — install with `npx shadcn@latest add` when you want polished primitives
- next-auth — only needed if you want server-side sessions (current setup uses localStorage JWT)
- WebSocket hooks for live chat / watch party — pattern is in the openapi.yaml under `/ws/*`
- 22 pixel-perfect pages — only the 7 most important are scaffolded. Use `distrebute-ui-templates.html` as the design reference; add the remaining pages on the same pattern.
