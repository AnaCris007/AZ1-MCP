import { AnimatePresence, motion } from 'framer-motion'
import { Monitor, Moon, PanelLeftClose, Sun, X } from 'lucide-react'
import Logo from '../Logo/Logo'
import Switch from '../Switch/Switch'

const THEME_OPTIONS = [
  { value: 'light', label: 'Claro', icon: Sun },
  { value: 'dark', label: 'Escuro', icon: Moon },
  { value: 'system', label: 'Sistema', icon: Monitor },
]

export default function SettingsModal({
  open,
  onClose,
  mode,
  onSetMode,
  settings,
  onUpdateSetting,
}) {
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 z-40 bg-black/30"
            onClick={onClose}
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0, y: 12, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 12, scale: 0.98 }}
              transition={{ duration: 0.18, ease: 'easeOut' }}
              role="dialog"
              aria-modal="true"
              aria-label="Configurações"
              className="w-full max-w-[440px] rounded-[28px] border border-border bg-surface p-6 shadow-xl"
            >
              <div className="mb-6 flex items-center justify-between">
                <h2 className="text-[17px] font-semibold text-text-primary">
                  Configurações
                </h2>
                <button
                  type="button"
                  onClick={onClose}
                  aria-label="Fechar"
                  className="flex h-8 w-8 items-center justify-center rounded-lg text-text-secondary transition-colors hover:bg-black/5 dark:hover:bg-white/10"
                >
                  <X size={17} strokeWidth={1.75} />
                </button>
              </div>

              <section className="mb-6">
                <p className="mb-2.5 text-[13px] font-medium text-text-secondary">
                  Aparência
                </p>
                <div className="flex rounded-xl bg-black/5 p-1 dark:bg-white/5">
                  {THEME_OPTIONS.map((option) => {
                    const Icon = option.icon
                    const isActive = mode === option.value
                    return (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => onSetMode(option.value)}
                        className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-[13px] font-medium transition-colors ${
                          isActive
                            ? 'bg-surface text-text-primary shadow-sm'
                            : 'text-text-secondary hover:text-text-primary'
                        }`}
                      >
                        <Icon size={14} strokeWidth={1.75} />
                        {option.label}
                      </button>
                    )
                  })}
                </div>
              </section>

              <section className="mb-6">
                <p className="mb-2.5 text-[13px] font-medium text-text-secondary">
                  Barra lateral
                </p>
                <div className="flex items-center justify-between rounded-xl border border-border-soft px-3.5 py-3">
                  <div className="flex items-center gap-2.5">
                    <PanelLeftClose
                      size={16}
                      strokeWidth={1.75}
                      className="shrink-0 text-text-secondary"
                    />
                    <span className="text-[14px] text-text-primary">
                      Iniciar recolhida
                    </span>
                  </div>
                  <Switch
                    checked={settings.startSidebarCollapsed}
                    onChange={(value) => onUpdateSetting('startSidebarCollapsed', value)}
                    label="Iniciar barra lateral recolhida"
                  />
                </div>
              </section>

              <section>
                <p className="mb-2.5 text-[13px] font-medium text-text-secondary">
                  Sobre
                </p>
                <div className="flex items-start gap-3 rounded-xl border border-border-soft px-3.5 py-3.5">
                  <Logo size={30} className="mt-0.5 shrink-0" />
                  <div>
                    <p className="text-[14px] font-medium text-text-primary">
                      AZ1 <span className="text-text-muted">v0.1.0</span>
                    </p>
                    <p className="mt-1 text-[13px] leading-relaxed text-text-secondary">
                      Assistente de IA para consulta de documentos, projetos e
                      processos do sistema metroviário.
                    </p>
                  </div>
                </div>
              </section>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  )
}
