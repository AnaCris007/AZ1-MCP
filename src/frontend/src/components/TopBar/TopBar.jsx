import { Check, LogOut, Moon, Settings, Share, SquarePen, Sun } from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'

export default function TopBar({
  title,
  onConfig,
  onShare,
  shareCopied,
  onNewChat,
  leftAccessory,
  theme,
  onToggleTheme,
}) {
  const { user, signOut } = useAuth()

  return (
    <div className="flex h-16 shrink-0 items-center justify-between border-b border-border-soft px-4 md:px-6">
      <div className="flex items-center gap-2">
        {leftAccessory}
        <span className="text-[15px] font-medium text-text-primary">{title}</span>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onToggleTheme}
          aria-label={theme === 'dark' ? 'Ativar modo claro' : 'Ativar modo escuro'}
          className="flex h-9 w-9 items-center justify-center rounded-full border border-border bg-surface text-text-primary transition-colors hover:bg-surface-hover"
        >
          {theme === 'dark' ? (
            <Sun size={15} strokeWidth={1.75} />
          ) : (
            <Moon size={15} strokeWidth={1.75} />
          )}
        </button>
        <button
          type="button"
          onClick={onConfig}
          className="hidden items-center gap-1.5 rounded-full border border-border bg-surface px-3.5 py-2 text-[13px] font-medium text-text-primary transition-colors hover:bg-surface-hover sm:flex"
        >
          <Settings size={14} strokeWidth={1.75} />
          Configurações
        </button>
        <button
          type="button"
          onClick={onShare}
          className="hidden items-center gap-1.5 rounded-full border border-border bg-surface px-3.5 py-2 text-[13px] font-medium text-text-primary transition-colors hover:bg-surface-hover sm:flex"
        >
          {shareCopied ? (
            <Check size={14} strokeWidth={1.75} />
          ) : (
            <Share size={14} strokeWidth={1.75} />
          )}
          {shareCopied ? 'Link copiado' : 'Compartilhar'}
        </button>
        <button
          type="button"
          onClick={onNewChat}
          className="flex items-center gap-1.5 rounded-full bg-button-primary px-3.5 py-2 text-[13px] font-medium text-button-primary-text transition-opacity hover:opacity-90"
        >
          Novo chat
          <SquarePen size={14} strokeWidth={1.75} />
        </button>
        {user && (
          <>
            <span
              className="hidden max-w-[160px] truncate text-[13px] text-text-secondary sm:inline"
              title={user.email}
            >
              {user.email}
            </span>
            <button
              type="button"
              onClick={() => void signOut()}
              aria-label="Sair da conta"
              className="flex h-9 w-9 items-center justify-center rounded-full border border-border bg-surface text-text-primary transition-colors hover:bg-surface-hover"
            >
              <LogOut size={15} strokeWidth={1.75} />
            </button>
          </>
        )}
      </div>
    </div>
  )
}
