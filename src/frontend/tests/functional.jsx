// Harness somente de desenvolvimento. Exercita o componente real e o cliente
// HTTP com backend indisponível; não representa login SSO nem usuário externo.
import React from 'react'
import { createRoot } from 'react-dom/client'
import { AuthProvider } from '../src/contexts/AuthContext'
import AgentPage from '../src/pages/AgentPage'
import '../src/index.css'

createRoot(document.getElementById('root')).render(
  <AuthProvider>
    <AgentPage />
  </AuthProvider>,
)
