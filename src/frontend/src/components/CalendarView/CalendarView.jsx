import { motion } from 'framer-motion'
import { CalendarDays, Clock3, Flag, MapPin, Plus, RefreshCw, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { createCalendarEvent, deleteCalendarEvent, fetchCalendarEvents } from '../../lib/api'
import CalendarGridView from './CalendarGridView'
import CreateEventModal from './CreateEventModal'
import EventDetailsModal from './EventDetailsModal'
import { DELETABLE_TYPES, TYPE_ACCENTS, TYPE_LABELS, TYPE_STYLES } from './calendarTypes'

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
  const [selection, setSelection] = useState(null)

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
    <div className="flex-1 overflow-y-auto px-3 sm:px-5">
      <div className="mx-auto flex min-h-full w-full max-w-[1000px] flex-col bg-background/95 px-3 pb-8 pt-3 shadow-[0_0_40px_rgba(15,23,42,0.04)] backdrop-blur-[2px] sm:px-5 sm:pt-4 dark:shadow-[0_0_40px_rgba(0,0,0,0.18)]">
        <div className="relative mb-3 flex flex-wrap items-center justify-between gap-3 overflow-hidden rounded-[18px] border border-blue-200/70 bg-gradient-to-br from-blue-50 via-white to-violet-50 px-4 py-3 shadow-sm dark:border-blue-400/15 dark:from-blue-950/55 dark:via-slate-950/75 dark:to-violet-950/45 sm:px-5">
          <div className="pointer-events-none absolute -right-10 -top-16 h-44 w-44 rounded-full bg-blue-400/15 blur-2xl dark:bg-blue-500/10" />
          <div className="relative flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600 text-white shadow-md shadow-blue-500/20">
              <CalendarDays size={18} strokeWidth={2} />
            </span>
            <div>
              <h1 className="text-[18px] font-semibold tracking-[-0.02em] text-slate-950 dark:text-white">Agenda</h1>
              <p className="hidden text-[11px] text-slate-500 dark:text-slate-400 sm:block">Compromissos, prazos e marcos</p>
            </div>
          </div>
          <div className="relative flex items-center gap-2">
            <div className="flex rounded-xl border border-slate-200/80 bg-white/80 p-1 shadow-sm backdrop-blur dark:border-white/10 dark:bg-white/5">
              {[{ value: 'list', label: 'Lista' }, { value: 'grid', label: 'Mês' }].map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setView(option.value)}
                  className={`rounded-lg px-3 py-1.5 text-[13px] font-medium transition-colors ${
                    view === option.value
                      ? 'bg-slate-900 text-white shadow-sm dark:bg-white dark:text-slate-950'
                      : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
            <button
              type="button"
              onClick={() => setCreating(true)}
              className="flex items-center gap-1.5 rounded-xl bg-blue-600 px-3 py-2 text-[12px] font-semibold text-white shadow-md shadow-blue-500/20 transition-colors hover:bg-blue-700"
            >
              <Plus size={14} strokeWidth={2} />
              Novo evento
            </button>
          </div>
        </div>

        {loading && (
          <div role="status" className="flex min-h-52 flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white/80 text-slate-500 dark:border-white/10 dark:bg-slate-950/45 dark:text-slate-400">
            <RefreshCw size={22} className="mb-3 animate-spin text-blue-600" />
            <p className="text-[13px] font-medium">Carregando agenda...</p>
          </div>
        )}
        {error && <div role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 px-5 py-4 text-[13px] text-rose-700 dark:border-rose-500/25 dark:bg-rose-500/10 dark:text-rose-300">{error}</div>}
        {!loading && !error && days.length === 0 && (
          <div className="flex min-h-56 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white/65 px-6 text-center dark:border-white/15 dark:bg-slate-950/35">
            <span className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-300"><CalendarDays size={22} /></span>
            <p className="text-[14px] font-semibold text-slate-800 dark:text-slate-100">Sua agenda está livre</p>
            <p className="mt-1 text-[12px] text-slate-500 dark:text-slate-400">Nenhum marco, prazo ou evento registrado.</p>
          </div>
        )}

        {!loading && !error && view === 'grid' && (
          <CalendarGridView
            visibleMonth={visibleMonth}
            onPrevMonth={() => setVisibleMonth((mes) => new Date(mes.getFullYear(), mes.getMonth() - 1, 1))}
            onNextMonth={() => setVisibleMonth((mes) => new Date(mes.getFullYear(), mes.getMonth() + 1, 1))}
            days={days}
            onDeleteEvent={handleDelete}
            onSelectEvent={(event, day) => setSelection({ event, day })}
          />
        )}

        {!loading && !error && view === 'list' && (
          <div className="flex flex-col gap-4">
            {days.map((day, dayIndex) => (
              <motion.div
                key={day.date}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, delay: dayIndex * 0.04, ease: 'easeOut' }}
              >
                <div className="mb-2 flex items-center gap-2">
                  <div className="h-px flex-1 bg-slate-200 dark:bg-white/10" />
                  <div className="flex items-baseline gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 shadow-sm dark:border-white/10 dark:bg-slate-900">
                    <p className="text-[12px] font-semibold capitalize text-slate-900 dark:text-white">{day.date}</p>
                    <p className="text-[10px] capitalize text-slate-400 dark:text-slate-500">{day.weekday}</p>
                  </div>
                  <div className="h-px flex-1 bg-slate-200 dark:bg-white/10" />
                </div>

                <div className="flex flex-col gap-1.5">
                  {day.events.map((event) => (
                    <div
                      key={event.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => setSelection({ event, day })}
                      onKeyDown={(keyEvent) => {
                        if (keyEvent.key === 'Enter' || keyEvent.key === ' ') {
                          keyEvent.preventDefault()
                          setSelection({ event, day })
                        }
                      }}
                      className="group relative flex cursor-pointer items-center gap-2.5 overflow-hidden rounded-xl border border-slate-200 bg-white px-3 py-2.5 shadow-sm transition-colors hover:border-blue-300 hover:bg-blue-50/30 focus:outline-none focus:ring-2 focus:ring-blue-500/30 dark:border-white/10 dark:bg-slate-950/55 dark:hover:border-blue-400/30 dark:hover:bg-blue-500/5 sm:px-4"
                    >
                      <span className={`absolute inset-y-0 left-0 w-1 ${TYPE_ACCENTS[event.type] ?? TYPE_ACCENTS.evento}`} />
                      <div className="flex w-[52px] shrink-0 items-center gap-1.5 text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                        <Clock3 size={13} strokeWidth={2} className="text-slate-400" />
                        <span>{event.time || '--:--'}</span>
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[13px] font-semibold text-slate-900 dark:text-white">
                          {event.title}
                        </p>
                        <div className="mt-0.5 flex items-center gap-1.5 text-[10px] text-slate-400 dark:text-slate-500">
                          <MapPin size={12} strokeWidth={1.75} />
                          <span className="truncate">{event.project}</span>
                        </div>
                      </div>
                      <span
                        className={`hidden shrink-0 items-center gap-1 rounded-full px-2.5 py-1 text-[10px] font-semibold sm:flex ${TYPE_STYLES[event.type] ?? TYPE_STYLES.evento}`}
                      >
                        <Flag size={11} strokeWidth={2} />
                        {TYPE_LABELS[event.type]}
                      </span>
                      {DELETABLE_TYPES.has(event.type) && (
                        <button
                          type="button"
                          onClick={(clickEvent) => {
                            clickEvent.stopPropagation()
                            handleDelete(event.id)
                          }}
                          aria-label={`Excluir ${event.title}`}
                          className="shrink-0 rounded-lg p-1.5 text-slate-300 opacity-70 transition-all hover:bg-rose-50 hover:text-rose-500 hover:opacity-100 dark:text-slate-600 dark:hover:bg-rose-500/10 dark:hover:text-rose-300 sm:opacity-0 sm:group-hover:opacity-100 sm:focus:opacity-100"
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
      <EventDetailsModal selection={selection} onClose={() => setSelection(null)} />
    </div>
  )
}
