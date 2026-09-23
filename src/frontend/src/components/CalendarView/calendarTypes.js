// Hoisted para fora de CalendarView.jsx porque CalendarGridView.jsx também
// precisa: as duas visualizações não podem divergir na cor/rótulo de um tipo.

export const TYPE_STYLES = {
  prazo: 'bg-red-500/10 text-red-500 dark:text-red-400',
  marco: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
  evento: 'bg-violet-500/10 text-violet-500 dark:text-violet-400',
}

export const TYPE_LABELS = {
  prazo: 'Prazo',
  marco: 'Marco',
  evento: 'Evento',
}

// Só o tipo criado pelo próprio usuário pode ser apagado — marco e prazo são
// derivados (projeto, pendência), não linhas próprias.
export const DELETABLE_TYPES = new Set(['evento'])
