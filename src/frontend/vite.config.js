import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Dentro do compose, a API atende em http://api:8000 (nome do serviço na rede
  // do Docker); rodando no host, em 127.0.0.1:8010. O endereço vem do ambiente
  // para que o mesmo arquivo sirva aos dois casos — o contêiner de
  // desenvolvimento define VITE_DEV_API_PROXY, e quem roda `npm run dev` no host
  // não define nada e cai no padrão de sempre.
  const apiProxyTarget = process.env.VITE_DEV_API_PROXY ?? 'http://127.0.0.1:8010'

  // Bind mount de Windows e macOS não entrega eventos de inotify ao contêiner:
  // sem polling, o HMR nunca dispara e a página fica velha sem avisar. Polling
  // custa CPU, então fica atrás de uma variável em vez de ligado sempre.
  const usePolling = Boolean(process.env.VITE_USE_POLLING)

  // O projeto mantém um único .env na raiz do repositório (ver .env.example);
  // sem isto, o Vite procuraria por um .env dentro de src/frontend/ que não
  // existe, e SUPABASE_URL/SUPABASE_ANON_KEY ficariam sempre vazias ao rodar
  // `npm run dev` fora do Docker.
  const envDir = '../..'

  // '' (sem prefixo) faz o loadEnv devolver TODAS as chaves do .env, não só as
  // que já começam com VITE_ — é o que permite ler SUPABASE_URL diretamente,
  // sem duplicar a variável como VITE_SUPABASE_URL só para o frontend enxergar.
  const env = loadEnv(mode, envDir, '')

  // Dentro do contêiner de desenvolvimento (docker-compose.override.yml), quem
  // chega é VITE_SUPABASE_URL/VITE_SUPABASE_ANON_KEY — o compose já faz esse
  // remapeamento porque o bind mount ali não alcança o .env da raiz. O
  // fallback cobre os dois casos com o mesmo código, sem que um caminho
  // quebre o outro.
  const supabaseUrl = env.SUPABASE_URL || env.VITE_SUPABASE_URL || ''
  const supabaseAnonKey = env.SUPABASE_ANON_KEY || env.VITE_SUPABASE_ANON_KEY || ''
  const authDisabled = env.AZ1_AUTH_MODE === 'disabled'

  return {
    plugins: [react(), tailwindcss()],
    envDir,
    define: {
      'import.meta.env.VITE_SUPABASE_URL': JSON.stringify(supabaseUrl),
      'import.meta.env.VITE_SUPABASE_ANON_KEY': JSON.stringify(supabaseAnonKey),
      'import.meta.env.VITE_AUTH_DISABLED': JSON.stringify(String(authDisabled)),
    },
    server: {
      // Sem host, o Vite escuta só em 127.0.0.1 DENTRO do contêiner, e a porta
      // publicada não leva a lugar nenhum.
      host: true,
      proxy: {
        '/api': {
          target: apiProxyTarget,
          changeOrigin: true,
        },
      },
      watch: {
        usePolling,
      },
    },
  }
})
