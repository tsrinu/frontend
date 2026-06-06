import './globals.css'
import { AuthProvider } from '@/lib/auth-context'

export const metadata = {
  title: 'distrebute',
  description: 'Streaming platform for creators and viewers',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-bg text-white">
        <AuthProvider>
          <NavBar />
          {children}
        </AuthProvider>
      </body>
    </html>
  )
}

function NavBar() {
  return (
    <nav className="border-b border-bg3 bg-bg2 px-6 py-3 flex items-center gap-6">
      <a href="/" className="font-bold text-lg flex items-center gap-2">
        <span className="w-7 h-7 rounded-md bg-brand-grad inline-block" />
        distrebute
      </a>
      <div className="flex gap-4 text-sm text-gray-400">
        <a href="/" className="hover:text-white">Home</a>
        <a href="/wallet" className="hover:text-white">Wallet</a>
        <a href="/memberships/ch_mira" className="hover:text-white">Memberships</a>
        <a href="/inbox" className="hover:text-white">Inbox</a>
        <a href="/settings" className="hover:text-white">Settings</a>
      </div>
      <div className="ml-auto text-xs text-gray-500"><AuthBadge /></div>
    </nav>
  )
}

function AuthBadge() {
  return <a href="/signin" className="text-gray-400 hover:text-white">Sign in / Out →</a>
}
