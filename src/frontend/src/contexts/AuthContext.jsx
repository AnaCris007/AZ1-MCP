import { createContext, useContext, useEffect, useState } from 'react'
import { isSupabaseConfigured, supabase } from '../lib/supabase'

const AuthContext = createContext(null)
const authDisabled = import.meta.env.VITE_AUTH_DISABLED === 'true'
const developmentUser = {
  id: 'development-user',
  email: 'desenvolvimento@local',
  user_metadata: { name: 'Usuário de desenvolvimento' },
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(authDisabled ? developmentUser : null)
  const [loading, setLoading] = useState(!authDisabled)

  useEffect(() => {
    if (authDisabled) return undefined

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
      setLoading(false)
    })

    return () => subscription.unsubscribe()
  }, [])

  async function signInWithMicrosoft() {
    if (authDisabled) return
    if (!isSupabaseConfigured) {
      throw new Error('Autenticação Microsoft não configurada neste ambiente.')
    }

    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'azure',
      options: {
        // Sem router nesta aplicação (App.jsx renderiza uma única página):
        // volta para a própria origem, não para uma rota como /home.
        redirectTo: window.location.origin,
        scopes: 'email',
        queryParams: { prompt: 'select_account' },
      },
    })

    if (error) throw error
  }

  async function signOut() {
    if (authDisabled) return

    const { error } = await supabase.auth.signOut()
    if (error) throw error
  }

  return (
    <AuthContext.Provider value={{ user, loading, signInWithMicrosoft, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error('useAuth deve ser usado dentro de AuthProvider.')
  }

  return context
}
