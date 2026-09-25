import { ChevronLeft, ChevronRight, Clock3, Trash2 } from 'lucide-react'
import { DELETABLE_TYPES, TYPE_ACCENTS, TYPE_STYLES } from './calendarTypes'

const NOMES_MES = [
  'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
  'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
]

// Segunda a domingo, mesma ordem de _DIAS_DA_SEMANA no backend.
const CABECALHO_SEMANA = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']

function paraIso(data) {
  const ano = data.getFullYear()
  const mes = String(data.getMonth() + 1).padStart(2, '0')
  const dia = String(data.getDate()).padStart(2, '0')
  return `${ano}-${mes}-${dia}`
}

// Sextupla de semanas (42 dias) começando na segunda-feira anterior (ou igual)
// ao dia 1 do mês visível. `Date.getDay()` é 0=domingo..6=sábado; o ajuste
// abaixo o converte para uma contagem que começa na segunda.
function construirGrade(visibleMonth) {
  const primeiroDoMes = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth(), 1)
  const deslocamento = (primeiroDoMes.getDay() + 6) % 7
  const inicio = new Date(primeiroDoMes)
  inicio.setDate(inicio.getDate() - deslocamento)

  return Array.from({ length: 42 }, (_, indice) => {
    const data = new Date(inicio)
    data.setDate(data.getDate() + indice)
    return data
  })
}

export default function CalendarGridView({ visibleMonth, onPrevMonth, onNextMonth, days, onDeleteEvent, onSelectEvent = () => {} }) {
  const diasPorIso = new Map((days ?? []).map((dia) => [dia.iso, dia]))
  const grade = construirGrade(visibleMonth)
  const mesVisivel = visibleMonth.getMonth()
  const hojeIso = paraIso(new Date())

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-lg dark:border-white/10 dark:bg-slate-950/60">
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-white/10 dark:bg-white/[0.035]">
        <button
          type="button"
          onClick={onPrevMonth}
          aria-label="Mês anterior"
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 transition-colors hover:border-blue-300 hover:text-blue-700 dark:border-white/10 dark:bg-white/5 dark:text-slate-300"
        >
          <ChevronLeft size={18} strokeWidth={1.75} />
        </button>
        <p className="text-[13px] font-semibold capitalize text-slate-900 dark:text-white">
          {NOMES_MES[mesVisivel]} de {visibleMonth.getFullYear()}
        </p>
        <button
          type="button"
          onClick={onNextMonth}
          aria-label="Próximo mês"
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 transition-colors hover:border-blue-300 hover:text-blue-700 dark:border-white/10 dark:bg-white/5 dark:text-slate-300"
        >
          <ChevronRight size={18} strokeWidth={1.75} />
        </button>
      </div>

      <div className="overflow-x-auto">
      <div className="grid min-w-[700px] grid-cols-7 border-y border-slate-200 bg-white text-center text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500 dark:border-white/10 dark:bg-transparent dark:text-slate-400">
        {CABECALHO_SEMANA.map((rotulo, index) => (
          <div key={rotulo} className={`py-1.5 ${index > 4 ? 'bg-slate-50 text-slate-400 dark:bg-white/[0.025]' : ''}`}>{rotulo}</div>
        ))}
      </div>

      <div className="grid min-w-[700px] grid-cols-7 gap-px bg-slate-200 dark:bg-white/10">
        {grade.map((data) => {
          const iso = paraIso(data)
          const dia = diasPorIso.get(iso)
          const foraDoMes = data.getMonth() !== mesVisivel
          const hoje = iso === hojeIso
          const fimDeSemana = data.getDay() === 0 || data.getDay() === 6

          return (
            <div
              key={iso}
              className={`min-h-[82px] p-1.5 transition-colors ${
                foraDoMes
                  ? 'bg-slate-50/70 dark:bg-white/[0.015]'
                  : fimDeSemana
                    ? 'bg-slate-50 dark:bg-white/[0.025]'
                    : 'bg-white hover:bg-blue-50/50 dark:bg-slate-950/70 dark:hover:bg-blue-500/[0.06]'
              }`}
            >
              <div className="mb-1 flex items-center justify-between">
                <span
                  aria-current={hoje ? 'date' : undefined}
                  className={`flex h-6 min-w-6 items-center justify-center rounded-full px-1 text-[11px] font-semibold ${
                    hoje
                      ? 'bg-blue-600 text-white shadow-md shadow-blue-500/30'
                      : foraDoMes
                        ? 'text-slate-300 dark:text-slate-700'
                        : 'text-slate-600 dark:text-slate-300'
                  }`}
                >
                  {data.getDate()}
                </span>
                {(dia?.events?.length ?? 0) > 0 && (
                  <span className="text-[9px] font-semibold text-slate-400 dark:text-slate-500">
                    {dia.events.length} {dia.events.length === 1 ? 'item' : 'itens'}
                  </span>
                )}
              </div>
              <div className="flex flex-col gap-1">
                {(dia?.events ?? []).map((event) => (
                  <div
                    key={event.id}
                    title={event.title}
                    role="button"
                    tabIndex={0}
                    onClick={() => onSelectEvent(event, dia)}
                    onKeyDown={(keyEvent) => {
                      if (keyEvent.key === 'Enter' || keyEvent.key === ' ') {
                        keyEvent.preventDefault()
                        onSelectEvent(event, dia)
                      }
                    }}
                    className={`relative flex min-w-0 cursor-pointer items-center gap-1 overflow-hidden rounded-md py-1 pl-2.5 pr-1 text-[9px] font-semibold shadow-sm outline-none focus:ring-2 focus:ring-blue-500/40 ${TYPE_STYLES[event.type] ?? TYPE_STYLES.evento}`}
                  >
                    <span className={`absolute inset-y-0 left-0 w-1 ${TYPE_ACCENTS[event.type] ?? TYPE_ACCENTS.evento}`} />
                    {event.time && <Clock3 size={10} strokeWidth={2} className="shrink-0 opacity-70" />}
                    {event.time && <span className="shrink-0 opacity-70">{event.time}</span>}
                    <span className="min-w-0 truncate">{event.title}</span>
                    {DELETABLE_TYPES.has(event.type) && (
                      <button
                        type="button"
                        onClick={(clickEvent) => {
                          clickEvent.stopPropagation()
                          onDeleteEvent(event.id)
                        }}
                        aria-label={`Excluir ${event.title}`}
                        className="ml-auto shrink-0 rounded p-0.5 opacity-60 hover:bg-black/5 hover:opacity-100 dark:hover:bg-white/10"
                      >
                        <Trash2 size={11} strokeWidth={2} />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>
      </div>
    </div>
  )
}
