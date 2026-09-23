import { motion } from 'framer-motion'
import { CalendarDays, Flag, MapPin, Plus, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { createCalendarEvent, deleteCalendarEvent, fetchCalendarEvents } from '../../lib/api'
import CalendarGridView from './CalendarGridView'
import CreateEventModal from './CreateEventModal'
import { DELETABLE_TYPES, TYPE_LABELS, TYPE_STYLES } from './calendarTypes'

function startOfMonth(data) {
  return new Date(data.getFullYear(), data.getMonth(), 1)
}

function idNumerico(idComposto) {
  return idComposto.replace(/^evento-/, '')
}

export default function CalendarView() {
  const [days, setDays] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [view, setView] = useState('list')
  const [visibleMonth, setVisibleMonth] = useState(() => startOfMonth(new Date()))
  const [creating, setCreating] = useState(false)

  const loadAgenda = () => {
    setError('')
    return fetchCalendarEvents()
      .then((data) => {
        // A resposta vem como {days: [...]}; o componente lista os dias.
        setDays(data.days ?? [])
        setLoading(false)
      })
      .catch(() => {
        console.error('[calendar] não foi possível carregar a agenda do portfólio')
        setLoading(false)
        setError('Não foi possível carregar a agenda. Tente novamente ao abrir esta tela.')
      })
  }

  useEffect(() => {
    loadAgenda()
  }, [])

  const handleCreate = async (payload) => {
    await createCalendarEvent(payload)
    setCreating(false)
    await loadAgenda()
  }

  const handleDelete = async (eventId) => {
    const anterior = days
    setDays((prev) => prev.map((day) => ({ ...day, events: day.events.filter((event) => event.id !== eventId) })))
    try {
      await deleteCalendarEvent(idNumerico(eventId))
    } catch {
      setDays(anterior)
      setError('Não foi possível excluir o evento. Tente novamente.')
    }
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 pb-10 pt-6">
      <div className="mx-auto flex w-full max-w-[720px] flex-col">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <CalendarDays size={20} strokeWidth={1.75} className="text-text-primary" />
            <h1 className="text-[18px] font-semibold text-text-primary">Agenda</h1>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex rounded-xl bg-black/5 p-1 dark:bg-white/5">
              {[{ value: 'list', label: 'Lista' }, { value: 'grid', label: 'Mês' }].map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setView(option.value)}
                  className={`rounded-lg px-3 py-1.5 text-[13px] font-medium transition-colors ${
                    view === option.value
                      ? 'bg-surface text-text-primary shadow-sm'
                      : 'text-text-secondary hover:text-text-primary'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
            <button
              type="button"
              onClick={() => setCreating(true)}
              className="flex items-center gap-1.5 rounded-xl bg-button-primary px-3 py-1.5 text-[13px] font-medium text-button-primary-text transition-opacity hover:opacity-90"
            >
              <Plus size={14} strokeWidth={2} />
              Novo evento
            </button>
          </div>
        </div>

        {loading && <p role="status">Carregando agenda...</p>}
        {error && <p role="alert">{error}</p>}
        {!loading && !error && days.length === 0 && <p>Nenhum marco, prazo ou evento registrado.</p>}

        {!loading && !error && view === 'grid' && (
          <CalendarGridView
            visibleMonth={visibleMonth}
            onPrevMonth={() => setVisibleMonth((mes) => new Date(mes.getFullYear(), mes.getMonth() - 1, 1))}
            onNextMonth={() => setVisibleMonth((mes) => new Date(mes.getFullYear(), mes.getMonth() + 1, 1))}
            days={days}
            onDeleteEvent={handleDelete}
          />
        )}

        {!loading && !error && view === 'list' && (
          <div className="flex flex-col gap-6">
            {days.map((day, dayIndex) => (
              <motion.div
                key={day.date}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, delay: dayIndex * 0.04, ease: 'easeOut' }}
              >
                <div className="mb-2.5 flex items-baseline gap-2">
                  <p className="text-[14px] font-semibold text-text-primary">{day.date}</p>
                  <p className="text-[13px] text-text-muted">{day.weekday}</p>
                </div>

                <div className="flex flex-col gap-2">
                  {day.events.map((event) => (
                    <div
                      key={event.id}
                      className="flex items-start gap-3 rounded-xl border border-border-soft bg-surface px-4 py-3"
                    >
                      <span className="mt-0.5 w-12 shrink-0 text-[13px] font-medium text-text-secondary">
                        {event.time}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[14px] font-medium text-text-primary">
                          {event.title}
                        </p>
                        <div className="mt-1 flex items-center gap-2 text-[12px] text-text-muted">
                          <MapPin size={12} strokeWidth={1.75} />
                          <span className="truncate">{event.project}</span>
                        </div>
                      </div>
                      <span
                        className={`flex shrink-0 items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-medium ${TYPE_STYLES[event.type]}`}
                      >
                        <Flag size={11} strokeWidth={2} />
                        {TYPE_LABELS[event.type]}
                      </span>
                      {DELETABLE_TYPES.has(event.type) && (
                        <button
                          type="button"
                          onClick={() => handleDelete(event.id)}
                          aria-label={`Excluir ${event.title}`}
                          className="shrink-0 text-text-muted transition-colors hover:text-red-500"
                        >
                          <Trash2 size={15} strokeWidth={1.75} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      <CreateEventModal open={creating} onClose={() => setCreating(false)} onCreate={handleCreate} />
    </div>
  )
}
