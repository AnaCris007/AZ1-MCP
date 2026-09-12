import { AuthProvider, useAuth } from './contexts/AuthContext'
import LoginScreen from './components/LoginScreen/LoginScreen'
import AgentPage from './pages/AgentPage'

function Gate() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background text-text-secondary">
        Carregando...
      </div>
    )
  }

  return user ? <AgentPage /> : <LoginScreen />
}

export default function App() {
  return (
    <AuthProvider>
      <Gate />
    </AuthProvider>
  )
}
