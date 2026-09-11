import { AlertCircle, LogIn } from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import metroMapPattern from '../../assets/metro-map-pattern.svg'
import Logo from '../Logo/Logo'

export default function LoginScreen() {
  const { signInWithMicrosoft } = useAuth()
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleLogin() {
    setError(null)
    setLoading(true)

    try {
      await signInWithMicrosoft()
      // Em caso de sucesso o navegador é redirecionado para fora desta
      // página; não há um estado de "concluído" para exibir aqui.
    } catch {
      setError('Não foi possível iniciar o login. Tente novamente em instantes.')
      setLoading(false)
    }
  }

  return (
    <div
      className="flex h-screen w-full flex-col items-center justify-center gap-6 bg-background px-4 text-text-primary"
      style={{
        backgroundImage: `url("${metroMapPattern}")`,
        backgroundRepeat: 'repeat',
        backgroundSize: '340px 340px',
      }}
    >
      <div className="flex w-full max-w-sm flex-col items-center gap-6 rounded-2xl border border-border bg-surface px-8 py-10 text-center shadow-sm">
        <Logo size={48} />

        <div>
          <h1 className="text-[17px] font-medium text-text-primary">Acessar o AZ1</h1>
          <p className="mt-1 text-[13px] text-text-secondary">
            Entre com sua conta Microsoft para consultar o portfólio de projetos.
          </p>
        </div>

        {error && (
          <div
            role="alert"
            className="flex w-full items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-left text-[13px] text-red-700 dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-300"
          >
            <AlertCircle size={16} strokeWidth={1.75} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <button
          type="button"
          disabled={loading}
          onClick={() => void handleLogin()}
          className="flex w-full items-center justify-center gap-2 rounded-full bg-button-primary px-4 py-2.5 text-[14px] font-medium text-button-primary-text transition-opacity hover:opacity-90 disabled:opacity-60"
        >
          <LogIn size={16} strokeWidth={1.75} />
          {loading ? 'Redirecionando...' : 'Entrar com Microsoft'}
        </button>
      </div>
    </div>
  )
}
