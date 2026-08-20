import { useEffect, useState } from 'react'

import { AppShell } from './components/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { DisputeDetailPage } from './pages/DisputeDetailPage'
import { PlaceholderPage } from './pages/PlaceholderPage'

function currentRoute() { return window.location.hash.replace(/^#/, '') || '/disputes' }

export default function App() {
  const [route, setRoute] = useState(currentRoute)
  useEffect(() => { const update = () => setRoute(currentRoute()); window.addEventListener('hashchange', update); return () => window.removeEventListener('hashchange', update) }, [])
  const content = route.startsWith('/disputes/') ? <DisputeDetailPage recordId={route.split('/').at(-1)} /> : route === '/analytics' ? <PlaceholderPage title="Collections analytics" /> : route === '/activity' ? <PlaceholderPage title="Recent activity" /> : route === '/settings' ? <PlaceholderPage title="Workspace settings" /> : <DashboardPage />
  return <AppShell route={route.startsWith('/disputes/') ? '/disputes' : route}>{content}</AppShell>
}
