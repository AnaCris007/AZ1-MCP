import { AnimatePresence, motion } from 'framer-motion'
import { CalendarDays, Clock3, Flag, FolderKanban, UserRound, X } from 'lucide-react'
import { useEffect } from 'react'
import { TYPE_LABELS, TYPE_STYLES } from './calendarTypes'

function DetailRow({ icon: Icon, label, children }) {
  if (!children) return null

  return (
    <div className="flex gap-3 py-2.5">
      <Icon size={15} className="mt-0.5 shrink-0 text-slate-400" />
      <div className="min-w-0">
        <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-400">{label}</p>
        <p className="mt-0.5 text-[13px] leading-relaxed text-slate-700 dark:text-slate-200">{children}</p>
      </div>
    </div>
  )
}

export default function EventDetailsModal({ selection, onClose }) {
  useEffect(() => {
    if (!selection) return undefined
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selection, onClose])

  const event = selection?.event
  const day = selection?.day

  return (
    <AnimatePresence>
      {event && (
        <>
          <motion.div
            className="fixed inset-0 z-40 bg-slate-950/35 backdrop-blur-[2px]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <div
            data-testid="event-details-modal-layer"
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            onClick={onClose}
          >
            <motion.section
              onClick={(event) => event.stopPropagation()}
              role="dialog"
              aria-modal="true"
              aria-labelledby="event-details-title"
              initial={{ opacity: 0, y: 10, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.98 }}
              className="w-full max-w-[420px] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-white/10 dark:bg-slate-900"
            >
              <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-5 py-4 dark:border-white/10">
                <div className="min-w-0">
                  <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${TYPE_STYLES[event.type] ?? TYPE_STYLES.evento}`}>
                    <Flag size={10} /> {TYPE_LABELS[event.type] ?? 'Compromisso'}
                  </span>
                  <h2 id="event-details-title" className="mt-2 text-[17px] font-semibold leading-snug text-slate-950 dark:text-white">
                    {event.title}
                  </h2>
                </div>
                <button type="button" onClick={onClose} aria-label="Fechar detalhes" className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-white/10 dark:hover:text-white">
                  <X size={17} />
                </button>
              </div>

              <div className="divide-y divide-slate-100 px-5 dark:divide-white/10">
                <DetailRow icon={CalendarDays} label="Data">{day?.date ? `${day.date}, ${day.weekday}` : ''}</DetailRow>
                <DetailRow icon={Clock3} label="Horário">{event.time || 'Dia inteiro'}</DetailRow>
                <DetailRow icon={FolderKanban} label="Projeto">{event.project}</DetailRow>
                <DetailRow icon={UserRound} label="Responsável">{event.responsible}</DetailRow>
                <DetailRow icon={Flag} label="Status">{event.status}</DetailRow>
              </div>

              {event.description && (
                <div className="border-t border-slate-100 bg-slate-50/70 px-5 py-4 dark:border-white/10 dark:bg-white/[0.025]">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-400">Detalhes</p>
                  <p className="mt-1.5 whitespace-pre-wrap text-[13px] leading-relaxed text-slate-600 dark:text-slate-300">{event.description}</p>
                </div>
              )}
            </motion.section>
          </div>
        </>
      )}
    </AnimatePresence>
  )
}
