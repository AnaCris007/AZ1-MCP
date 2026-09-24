import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY
export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey)

if (!isSupabaseConfigured) {
  console.error(
    'VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY não configuradas — o login com ' +
      'Microsoft não vai funcionar. Preencha as duas no .env (ver .env.example).',
  )
}

// sessionStorage em vez do padrão (localStorage): a sessão morre ao fechar a
// aba, o que reduz a janela de um token roubado por XSS. Custo aceito: reabrir
// em outra aba pede login de novo.
export const supabase = createClient(
  supabaseUrl || 'https://placeholder.supabase.co',
  supabaseAnonKey || 'placeholder-anon-key',
  {
    auth: {
      storage: window.sessionStorage,
      flowType: 'pkce',
    },
  },
)
