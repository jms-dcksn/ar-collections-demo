import { BarChart3, Bell, CircleDollarSign, LayoutDashboard, Settings } from 'lucide-react'
import type { ReactNode } from 'react'

import { useWorkspace } from '../workspace'

const nav = [
  ['/disputes', 'Disputes', LayoutDashboard], ['/analytics', 'Analytics', BarChart3], ['/activity', 'Activity', Bell], ['/settings', 'Settings', Settings],
] as const

export function AppShell({ children, route }: { children: ReactNode; route: string }) {
  const { authenticated, login, logout } = useWorkspace()
  return <div className="app-shell"><aside className="rail"><div className="brand"><span className="brand-mark"><CircleDollarSign size={18} /></span>Collections<br />Command</div><nav>{nav.map(([to, label, Icon]) => <a key={to} href={`#${to}`} className={`nav-link ${route === to ? 'active' : ''}`}><Icon size={17} />{label}</a>)}</nav><div className="rail-foot">AR resolution workspace<br />Secure UiPath session</div></aside><main className="content"><header className="topbar"><span className="subtle">Operations / Accounts receivable</span><div className="user"><span className="avatar">JD</span><span>{authenticated ? 'UiPath user' : 'Preview user'}</span><button className="text-button" onClick={() => void (authenticated ? logout() : login())}>{authenticated ? 'Log out' : 'Log in'}</button></div></header>{children}</main></div>
}
