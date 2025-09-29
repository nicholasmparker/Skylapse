import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
// Import configuration early to ensure it's loaded and exposed globally
import './config/environment'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
