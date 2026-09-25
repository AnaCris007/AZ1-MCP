// Hoisted para fora de CalendarView.jsx porque CalendarGridView.jsx também
// precisa: as duas visualizações não podem divergir na cor/rótulo de um tipo.

export const TYPE_STYLES = {
  prazo: 'border border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/25 dark:bg-rose-500/15 dark:text-rose-300',
  marco: 'border border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/25 dark:bg-amber-500/15 dark:text-amber-300',
  evento: 'border border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-500/25 dark:bg-violet-500/15 dark:text-violet-300',
}

export const TYPE_ACCENTS = {
  prazo: 'bg-rose-500',
  marco: 'bg-amber-500',
  evento: 'bg-violet-500',
}

export const TYPE_LABELS = {
  prazo: 'Prazo',
  marco: 'Marco',
  evento: 'Evento',
}

// Só o tipo criado pelo próprio usuário pode ser apagado — marco e prazo são
// derivados (projeto, pendência), não linhas próprias.
export const DELETABLE_TYPES = new Set(['evento'])
