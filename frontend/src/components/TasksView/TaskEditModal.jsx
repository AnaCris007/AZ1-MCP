import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { useEffect, useState } from 'react'

const PRIORITY_OPTIONS = [
  { value: 'alta', label: 'Alta' },
  { value: 'media', label: 'Média' },
  { value: 'baixa', label: 'Baixa' },
]

const EMPTY_FORM = {
  title: '',
  project: '',
  priority: 'media',
  dueDate: '',
  description: '',
}

export default function TaskEditModal({ open, task, onClose, onSave }) {
  const [form, setForm] = useState(EMPTY_FORM)

  useEffect(() => {
    if (open) {
      setForm({
        title: task?.title ?? '',
        project: task?.project ?? '',
        priority: task?.priority ?? 'media',
        dueDate: task?.dueDate ?? '',
        description: task?.description ?? '',
      })
    }
  }, [open, task])

  const updateField = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!form.title.trim()) return
    onSave({ ...form, title: form.title.trim() })
  }

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
            <motion.form
              onSubmit={handleSubmit}
              initial={{ opacity: 0, y: 12, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 12, scale: 0.98 }}
              transition={{ duration: 0.18, ease: 'easeOut' }}
              role="dialog"
              aria-modal="true"
              aria-label="Editar tarefa"
              className="w-full max-w-[440px] rounded-[28px] border border-border bg-surface p-6 shadow-xl"
            >
              <div className="mb-6 flex items-center justify-between">
                <h2 className="text-[17px] font-semibold text-text-primary">
                  Editar tarefa
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

              <div className="mb-4">
                <label
                  htmlFor="task-title"
                  className="mb-1.5 block text-[13px] font-medium text-text-secondary"
                >
                  Título
                </label>
                <input
                  id="task-title"
                  type="text"
                  autoFocus
                  value={form.title}
                  onChange={(e) => updateField('title', e.target.value)}
                  placeholder="Ex.: Atualizar status de risco"
                  className="w-full rounded-xl border border-border-soft bg-transparent px-3.5 py-2.5 text-[14px] text-text-primary placeholder:text-text-muted focus:border-text-secondary focus:outline-none"
                />
              </div>

              <div className="mb-4">
                <label
                  htmlFor="task-project"
                  className="mb-1.5 block text-[13px] font-medium text-text-secondary"
                >
                  Projeto
                </label>
                <input
                  id="task-project"
                  type="text"
                  value={form.project}
                  onChange={(e) => updateField('project', e.target.value)}
                  placeholder="Ex.: Linha 6 — Laranja"
                  className="w-full rounded-xl border border-border-soft bg-transparent px-3.5 py-2.5 text-[14px] text-text-primary placeholder:text-text-muted focus:border-text-secondary focus:outline-none"
                />
              </div>

              <div className="mb-4 flex gap-3">
                <div className="flex-1">
                  <p className="mb-1.5 text-[13px] font-medium text-text-secondary">
                    Prioridade
                  </p>
                  <div className="flex rounded-xl bg-black/5 p-1 dark:bg-white/5">
                    {PRIORITY_OPTIONS.map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => updateField('priority', option.value)}
                        className={`flex-1 rounded-lg py-2 text-[13px] font-medium transition-colors ${
                          form.priority === option.value
                            ? 'bg-surface text-text-primary shadow-sm'
                            : 'text-text-secondary hover:text-text-primary'
                        }`}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="w-[140px]">
                  <label
                    htmlFor="task-due-date"
                    className="mb-1.5 block text-[13px] font-medium text-text-secondary"
                  >
                    Prazo
                  </label>
                  <input
                    id="task-due-date"
                    type="date"
                    value={form.dueDate}
                    onChange={(e) => updateField('dueDate', e.target.value)}
                    className="w-full rounded-xl border border-border-soft bg-transparent px-3 py-2.5 text-[13px] text-text-primary focus:border-text-secondary focus:outline-none"
                  />
                </div>
              </div>

              <div className="mb-6">
                <label
                  htmlFor="task-description"
                  className="mb-1.5 block text-[13px] font-medium text-text-secondary"
                >
                  Detalhes
                </label>
                <textarea
                  id="task-description"
                  rows={3}
                  value={form.description}
                  onChange={(e) => updateField('description', e.target.value)}
                  placeholder="Contexto, próximos passos ou observações do agente..."
                  className="w-full resize-none rounded-xl border border-border-soft bg-transparent px-3.5 py-2.5 text-[14px] leading-relaxed text-text-primary placeholder:text-text-muted focus:border-text-secondary focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-xl border border-border px-4 py-2 text-[13px] font-medium text-text-primary transition-colors hover:bg-surface-hover"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="rounded-xl bg-button-primary px-4 py-2 text-[13px] font-medium text-button-primary-text transition-opacity hover:opacity-90"
                >
                  Salvar
                </button>
              </div>
            </motion.form>
          </div>
        </>
      )}
    </AnimatePresence>
  )
}
