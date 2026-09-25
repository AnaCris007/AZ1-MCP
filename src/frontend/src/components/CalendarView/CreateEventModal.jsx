import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { useState } from 'react'

const EMPTY_FORM = {
  title: '',
  date: '',
  time: '',
  description: '',
}

export default function CreateEventModal({ open, onClose, onCreate }) {
  const [form, setForm] = useState(EMPTY_FORM)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const updateField = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  const handleClose = () => {
    setForm(EMPTY_FORM)
    setError('')
    onClose()
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const title = form.title.trim()
    if (!title || !form.date) return

    setSaving(true)
    setError('')
    try {
      await onCreate({ title, date: form.date, time: form.time, description: form.description.trim() })
      setForm(EMPTY_FORM)
    } catch {
      setError('Não foi possível criar o evento. Tente novamente.')
    } finally {
      setSaving(false)
    }
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
            onClick={handleClose}
          />
          <div
            data-testid="create-event-modal-layer"
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            onClick={handleClose}
          >
            <motion.form
              onClick={(event) => event.stopPropagation()}
              onSubmit={handleSubmit}
              initial={{ opacity: 0, y: 12, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 12, scale: 0.98 }}
              transition={{ duration: 0.18, ease: 'easeOut' }}
              role="dialog"
              aria-modal="true"
              aria-label="Novo evento"
              className="w-full max-w-[440px] rounded-[28px] border border-border bg-surface p-6 shadow-xl"
            >
              <div className="mb-6 flex items-center justify-between">
                <h2 className="text-[17px] font-semibold text-text-primary">
                  Novo evento
                </h2>
                <button
                  type="button"
                  onClick={handleClose}
                  aria-label="Fechar"
                  className="flex h-8 w-8 items-center justify-center rounded-lg text-text-secondary transition-colors hover:bg-black/5 dark:hover:bg-white/10"
                >
                  <X size={17} strokeWidth={1.75} />
                </button>
              </div>

              <div className="mb-4">
                <label
                  htmlFor="event-title"
                  className="mb-1.5 block text-[13px] font-medium text-text-secondary"
                >
                  Título
                </label>
                <input
                  id="event-title"
                  type="text"
                  autoFocus
                  value={form.title}
                  onChange={(e) => updateField('title', e.target.value)}
                  placeholder="Ex.: Reunião com o fornecedor"
                  className="w-full rounded-xl border border-border-soft bg-transparent px-3.5 py-2.5 text-[14px] text-text-primary placeholder:text-text-muted focus:border-text-secondary focus:outline-none"
                />
              </div>

              <div className="mb-4 flex gap-3">
                <div className="flex-1">
                  <label
                    htmlFor="event-date"
                    className="mb-1.5 block text-[13px] font-medium text-text-secondary"
                  >
                    Data
                  </label>
                  <input
                    id="event-date"
                    type="date"
                    value={form.date}
                    onChange={(e) => updateField('date', e.target.value)}
                    className="w-full rounded-xl border border-border-soft bg-transparent px-3 py-2.5 text-[13px] text-text-primary focus:border-text-secondary focus:outline-none"
                  />
                </div>
                <div className="w-[120px]">
                  <label
                    htmlFor="event-time"
                    className="mb-1.5 block text-[13px] font-medium text-text-secondary"
                  >
                    Hora
                  </label>
                  <input
                    id="event-time"
                    type="time"
                    value={form.time}
                    onChange={(e) => updateField('time', e.target.value)}
                    className="w-full rounded-xl border border-border-soft bg-transparent px-3 py-2.5 text-[13px] text-text-primary focus:border-text-secondary focus:outline-none"
                  />
                </div>
              </div>

              <div className="mb-6">
                <label
                  htmlFor="event-description"
                  className="mb-1.5 block text-[13px] font-medium text-text-secondary"
                >
                  Detalhes
                </label>
                <textarea
                  id="event-description"
                  rows={3}
                  value={form.description}
                  onChange={(e) => updateField('description', e.target.value)}
                  placeholder="Opcional"
                  className="w-full resize-none rounded-xl border border-border-soft bg-transparent px-3.5 py-2.5 text-[14px] leading-relaxed text-text-primary placeholder:text-text-muted focus:border-text-secondary focus:outline-none"
                />
              </div>

              {error && <p role="alert" className="mb-4 text-[13px] text-red-500">{error}</p>}

              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={handleClose}
                  className="rounded-xl border border-border px-4 py-2 text-[13px] font-medium text-text-primary transition-colors hover:bg-surface-hover"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={saving || !form.title.trim() || !form.date}
                  className="rounded-xl bg-button-primary px-4 py-2 text-[13px] font-medium text-button-primary-text transition-opacity hover:opacity-90 disabled:opacity-50"
                >
                  {saving ? 'Criando...' : 'Criar'}
                </button>
              </div>
            </motion.form>
          </div>
        </>
      )}
    </AnimatePresence>
  )
}
