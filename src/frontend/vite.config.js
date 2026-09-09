import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
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

export default defineConfig({
  plugins: [react(), tailwindcss()],
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
})
