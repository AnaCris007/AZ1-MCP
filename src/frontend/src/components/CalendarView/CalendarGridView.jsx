import { ChevronLeft, ChevronRight, Trash2 } from 'lucide-react'
import { DELETABLE_TYPES, TYPE_STYLES } from './calendarTypes'

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

export default function CalendarGridView({ visibleMonth, onPrevMonth, onNextMonth, days, onDeleteEvent }) {
  const diasPorIso = new Map((days ?? []).map((dia) => [dia.iso, dia]))
  const grade = construirGrade(visibleMonth)
  const mesVisivel = visibleMonth.getMonth()

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={onPrevMonth}
          aria-label="Mês anterior"
          className="flex h-8 w-8 items-center justify-center rounded-lg text-text-secondary transition-colors hover:bg-black/5 dark:hover:bg-white/10"
        >
          <ChevronLeft size={18} strokeWidth={1.75} />
        </button>
        <p className="text-[14px] font-semibold text-text-primary">
          {NOMES_MES[mesVisivel]} de {visibleMonth.getFullYear()}
        </p>
        <button
          type="button"
          onClick={onNextMonth}
          aria-label="Próximo mês"
          className="flex h-8 w-8 items-center justify-center rounded-lg text-text-secondary transition-colors hover:bg-black/5 dark:hover:bg-white/10"
        >
          <ChevronRight size={18} strokeWidth={1.75} />
        </button>
      </div>

      <div className="grid grid-cols-7 gap-1 text-center text-[11px] font-medium text-text-muted">
        {CABECALHO_SEMANA.map((rotulo) => (
          <div key={rotulo}>{rotulo}</div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-1">
        {grade.map((data) => {
          const iso = paraIso(data)
          const dia = diasPorIso.get(iso)
          const foraDoMes = data.getMonth() !== mesVisivel

          return (
            <div
              key={iso}
              className={`min-h-[84px] rounded-xl border border-border-soft p-1.5 ${foraDoMes ? 'opacity-40' : ''}`}
            >
              <p className="mb-1 text-[11px] font-medium text-text-secondary">{data.getDate()}</p>
              <div className="flex flex-col gap-1">
                {(dia?.events ?? []).map((event) => (
                  <div
                    key={event.id}
                    className={`flex items-center justify-between gap-1 truncate rounded-md px-1.5 py-0.5 text-[10px] font-medium ${TYPE_STYLES[event.type]}`}
                  >
                    <span className="truncate">{event.title}</span>
                    {DELETABLE_TYPES.has(event.type) && (
                      <button
                        type="button"
                        onClick={() => onDeleteEvent(event.id)}
                        aria-label={`Excluir ${event.title}`}
                        className="shrink-0 opacity-70 hover:opacity-100"
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
  )
}
