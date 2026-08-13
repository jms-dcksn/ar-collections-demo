import { createRoot } from 'react-dom/client'

import './index.css'
import App from './App'
import { WorkspaceProvider } from './workspace'

createRoot(document.getElementById('root')!).render(<WorkspaceProvider><App /></WorkspaceProvider>)
