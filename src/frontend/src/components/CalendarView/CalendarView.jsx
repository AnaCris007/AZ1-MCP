import { motion } from 'framer-motion'
import { CalendarDays, Flag, MapPin } from 'lucide-react'
import { useEffect, useState } from 'react'
import { fetchCalendarEvents } from '../../lib/api'

const TYPE_STYLES = {
  prazo: 'bg-red-500/10 text-red-500 dark:text-red-400',
  marco: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
  reuniao: 'bg-blue-500/10 text-blue-500 dark:text-blue-400',
}

const TYPE_LABELS = {
  prazo: 'Prazo',
  marco: 'Marco',
  reuniao: 'Reunião',
}

const FALLBACK_DAYS = [
  {
    date: '26 de agosto',
    weekday: 'Quarta-feira',
    events: [
      {
        id: 'e1',
        time: '09:00',
        title: 'Entrega do relatório de status — Linha 6',
        type: 'prazo',
        project: 'Linha 6 — Laranja',
      },
      {
        id: 'e2',
        time: '14:30',
        title: 'Alinhamento com equipe de obras',
        type: 'reuniao',
        project: 'Linha 2 — Verde',
      },
    ],
  },
  {
    date: '28 de agosto',
    weekday: 'Sexta-feira',
    events: [
      {
        id: 'e3',
        time: '11:00',
        title: 'Conclusão da fase de licenciamento ambiental',
        type: 'marco',
        project: 'Linha 6 — Laranja',
      },
    ],
  },
  {
    date: '02 de setembro',
    weekday: 'Quarta-feira',
    events: [
      {
        id: 'e4',
        time: '10:00',
        title: 'Prazo para envio de documentação de risco',
        type: 'prazo',
        project: 'Linha 15 — Prata',
      },
      {
        id: 'e5',
        time: '16:00',
        title: 'Revisão de cronograma com PMO',
        type: 'reuniao',
        project: 'Linha 15 — Prata',
      },
    ],
  },
]

export default function CalendarView() {
  const [days, setDays] = useState(FALLBACK_DAYS)

  useEffect(() => {
    let cancelled = false

    fetchCalendarEvents()
      .then((data) => {
        if (!cancelled) setDays(data)
      })
      .catch(() => {
        console.info('[calendar] backend indisponível, usando dados de exemplo')
      })

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="flex-1 overflow-y-auto px-4 pb-10 pt-6">
      <div className="mx-auto flex w-full max-w-[720px] flex-col">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <CalendarDays size={20} strokeWidth={1.75} className="text-text-primary" />
            <h1 className="text-[18px] font-semibold text-text-primary">Agenda</h1>
          </div>
          <span className="rounded-full border border-border-soft px-3 py-1 text-[12px] font-medium text-text-muted">
            Dados de exemplo — integração com Google Calendar em breve
          </span>
        </div>

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
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  )
}
