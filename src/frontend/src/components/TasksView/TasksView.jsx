import { motion } from 'framer-motion'
import { AlertTriangle, Calendar, Check, CheckCircle2, CircleDashed, ListChecks, Pencil, RefreshCw, Sparkles } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { fetchTasks, updateTask } from '../../lib/api'
import TaskEditModal from './TaskEditModal'

const PRIORITY_ORDER = { alta: 0, media: 1, baixa: 2 }

const PRIORITY_STYLES = {
  alta: 'border border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/25 dark:bg-rose-500/15 dark:text-rose-300',
  media: 'border border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/25 dark:bg-amber-500/15 dark:text-amber-300',
  baixa: 'border border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/25 dark:bg-emerald-500/15 dark:text-emerald-300',
}

const PRIORITY_ACCENTS = {
  alta: 'bg-rose-500',
  media: 'bg-amber-500',
  baixa: 'bg-emerald-500',
}

const PRIORITY_LABELS = {
  alta: 'Alta',
  media: 'Média',
  baixa: 'Baixa',
}


function formatDueDate(dueDate) {
  if (!dueDate) return null
  const [year, month, day] = dueDate.split('-')
  return `${day}/${month}/${year}`
}

function isOverdue(task) {
  if (!task.dueDate || task.done) return false
  const today = new Date()
  const todayIso = [today.getFullYear(), String(today.getMonth() + 1).padStart(2, '0'), String(today.getDate()).padStart(2, '0')].join('-')
  return task.dueDate < todayIso
}

export default function TasksView() {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [savingIds, setSavingIds] = useState(new Set())
  const pendingUpdates = useRef(new Set())
  const [error, setError] = useState('')
  const [editingTaskId, setEditingTaskId] = useState(null)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    let cancelled = false

    fetchTasks()
      .then((data) => {
        if (!cancelled) { setTasks(data); setLoading(false) }
      })
      .catch(() => {
        // Antes isto caía numa lista fixa e mostrava tarefa inventada como se
        // fosse real. Numa ferramenta de PMO, lista vazia é mais honesta.
        console.error('[tasks] não foi possível carregar as pendências do portfólio')
        if (!cancelled) { setLoading(false); setError('Não foi possível carregar as tarefas. Tente novamente ao abrir esta tela.') }
      })

    return () => {
      cancelled = true
    }
  }, [])

  const sortedTasks = useMemo(
    () =>
      [...tasks].sort((a, b) => {
        if (a.done !== b.done) return a.done ? 1 : -1
        return PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority]
      }),
    [tasks],
  )

  const editingTask = tasks.find((task) => task.id === editingTaskId) ?? null
  const openCount = tasks.filter((task) => !task.done).length
  const doneCount = tasks.length - openCount
  const filteredTasks = sortedTasks.filter((task) => {
    if (filter === 'open') return !task.done
    if (filter === 'done') return task.done
    return true
  })

  const applyTaskUpdate = async (id, updates) => {
    const previous = tasks.find((task) => task.id === id)
    if (!previous || pendingUpdates.current.has(id)) return
    pendingUpdates.current.add(id)
    setSavingIds(new Set(pendingUpdates.current))
    setError('')
    setTasks((prev) => prev.map((task) => (task.id === id ? { ...task, ...updates } : task)))
    try {
      const atualizada = await updateTask(id, updates)
      setTasks((prev) => prev.map((task) => (task.id === id ? atualizada : task)))
    } catch {
      setTasks((prev) => prev.map((task) => (task.id === id ? previous : task)))
      setError('Não foi possível salvar a alteração. A tarefa mantém o estado anterior. Tente novamente.')
    } finally {
      pendingUpdates.current.delete(id)
      setSavingIds(new Set(pendingUpdates.current))
    }
  }

  const toggleTask = (id) => {
    const task = tasks.find((item) => item.id === id)
    if (!task) return
    applyTaskUpdate(id, { done: !task.done })
  }

  const handleSaveTask = (updates) => {
    applyTaskUpdate(editingTaskId, updates)
    setEditingTaskId(null)
  }

  return (
    <div className="flex-1 overflow-y-auto px-3 sm:px-5">
      <div className="mx-auto flex min-h-full w-full max-w-[1000px] flex-col bg-background/95 px-3 pb-8 pt-3 shadow-[0_0_40px_rgba(15,23,42,0.04)] backdrop-blur-[2px] sm:px-5 sm:pt-4 dark:shadow-[0_0_40px_rgba(0,0,0,0.18)]">
        <div className="relative mb-3 flex flex-wrap items-center justify-between gap-3 overflow-hidden rounded-[18px] border border-violet-200/70 bg-gradient-to-br from-violet-50 via-white to-blue-50 px-4 py-3 shadow-sm dark:border-violet-400/15 dark:from-violet-950/45 dark:via-slate-950/75 dark:to-blue-950/45 sm:px-5">
          <div className="pointer-events-none absolute -right-10 -top-16 h-44 w-44 rounded-full bg-violet-400/15 blur-2xl" />
          <div className="relative flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-600 text-white shadow-md shadow-violet-500/20">
              <ListChecks size={18} strokeWidth={2} />
            </span>
            <div>
              <h1 className="text-[18px] font-semibold tracking-[-0.02em] text-slate-950 dark:text-white">Tarefas</h1>
              <p className="hidden text-[11px] text-slate-500 dark:text-slate-400 sm:block">Pendências priorizadas do portfólio</p>
            </div>
          </div>
          <div className="relative flex items-center gap-2">
            <span className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white/75 px-2.5 py-1.5 text-[11px] font-semibold text-slate-600 dark:border-white/10 dark:bg-white/5 dark:text-slate-300">
              <CircleDashed size={12} className="text-violet-500" /> {openCount} abertas
            </span>
            <span className="hidden items-center gap-1.5 rounded-lg border border-slate-200 bg-white/75 px-2.5 py-1.5 text-[11px] font-semibold text-slate-600 dark:border-white/10 dark:bg-white/5 dark:text-slate-300 sm:flex">
              <CheckCircle2 size={12} className="text-emerald-500" /> {doneCount} concluídas
            </span>
          </div>
        </div>

        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="flex rounded-xl border border-slate-200 bg-white p-1 shadow-sm dark:border-white/10 dark:bg-white/5">
            {[
              { value: 'all', label: 'Todas', count: tasks.length },
              { value: 'open', label: 'Abertas', count: openCount },
              { value: 'done', label: 'Concluídas', count: doneCount },
            ].map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => setFilter(option.value)}
                aria-pressed={filter === option.value}
                className={`rounded-lg px-3 py-1.5 text-[11px] font-semibold transition-colors ${filter === option.value ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-950' : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'}`}
              >
                {option.label} <span className="ml-1 opacity-60">{option.count}</span>
              </button>
            ))}
          </div>
          <span className="flex items-center gap-1.5 text-[10px] font-medium text-slate-400">
            <Sparkles size={11} /> Sugeridas pelo agente
          </span>
        </div>

        {loading && <div role="status" className="flex min-h-40 flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white/75 text-slate-500 dark:border-white/10 dark:bg-slate-950/45"><RefreshCw size={20} className="mb-2 animate-spin text-violet-600" /><span className="text-[12px] font-medium">Carregando tarefas...</span></div>}
        {savingIds.size > 0 && <p role="status" className="fixed bottom-5 right-5 z-30 rounded-full bg-slate-900 px-3 py-1.5 text-[11px] font-medium text-white shadow-lg dark:bg-white dark:text-slate-900">Salvando alterações...</p>}
        {error && <div role="alert" className="mb-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-[12px] text-rose-700 dark:border-rose-500/25 dark:bg-rose-500/10 dark:text-rose-300">{error}</div>}
        <div className="flex flex-col gap-1.5">
          {filteredTasks.map((task, index) => (
            <motion.div
              key={task.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2, delay: index * 0.03, ease: 'easeOut' }}
              className={`group relative flex items-start gap-3 overflow-hidden rounded-xl border bg-white px-3 py-2.5 shadow-sm transition-colors dark:bg-slate-950/55 sm:px-4 ${
                task.done
                  ? 'border-slate-200 opacity-60 dark:border-white/10'
                  : 'border-slate-200 hover:border-violet-300 hover:bg-violet-50/20 dark:border-white/10 dark:hover:border-violet-400/30 dark:hover:bg-violet-500/5'
              }`}
            >
              <span className={`absolute inset-y-0 left-0 w-1 ${task.done ? 'bg-slate-300 dark:bg-slate-700' : PRIORITY_ACCENTS[task.priority] ?? PRIORITY_ACCENTS.media}`} />
              <button
                type="button"
                onClick={() => toggleTask(task.id)}
                disabled={savingIds.has(task.id)}
                aria-label={task.done ? 'Marcar como pendente' : 'Marcar como concluída'}
                aria-pressed={task.done}
                className={`mt-0.5 flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full border transition-colors ${
                  task.done
                    ? 'border-emerald-500 bg-emerald-500 text-white'
                    : 'border-slate-300 text-transparent hover:border-violet-500 dark:border-slate-600'
                }`}
              >
                <Check size={12} strokeWidth={2.5} />
              </button>

              <div className="min-w-0 flex-1">
                <p
                  className={`text-[13px] font-semibold text-slate-900 dark:text-white ${
                    task.done ? 'line-through' : ''
                  }`}
                >
                  {task.title}
                </p>
                {task.description && (
                  <p className="mt-0.5 line-clamp-2 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">
                    {task.description}
                  </p>
                )}
                <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-slate-400 dark:text-slate-500">
                  <span className="truncate">{task.project}</span>
                  {task.dueDate && (
                    <span className={`flex items-center gap-1 ${isOverdue(task) ? 'font-semibold text-rose-600 dark:text-rose-400' : ''}`}>
                      {isOverdue(task) ? <AlertTriangle size={11} /> : <Calendar size={11} strokeWidth={1.75} />}
                      {formatDueDate(task.dueDate)}
                      {isOverdue(task) && ' · vencida'}
                    </span>
                  )}
                </div>
              </div>

              <div className="flex shrink-0 items-center gap-2">
                <span
                  className={`rounded-full px-2 py-0.5 text-[9px] font-semibold ${PRIORITY_STYLES[task.priority] ?? PRIORITY_STYLES.media}`}
                >
                  {PRIORITY_LABELS[task.priority]}
                </span>
                <button
                  type="button"
                  onClick={() => setEditingTaskId(task.id)}
                  disabled={savingIds.has(task.id)}
                  aria-label="Editar tarefa"
                  className="flex h-7 w-7 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-violet-50 hover:text-violet-600 dark:hover:bg-violet-500/10 dark:hover:text-violet-300"
                >
                  <Pencil size={13} strokeWidth={1.75} />
                </button>
              </div>
            </motion.div>
          ))}

          {!loading && !error && filteredTasks.length === 0 && (
            <div className="flex min-h-40 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white/60 px-5 text-center dark:border-white/15 dark:bg-slate-950/35">
              <span className="mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-violet-50 text-violet-600 dark:bg-violet-500/10 dark:text-violet-300"><CheckCircle2 size={19} /></span>
              <p className="text-[12px] font-medium text-slate-500 dark:text-slate-400">
                {tasks.length === 0 ? 'Nenhuma tarefa sugerida no momento.' : 'Nenhuma tarefa neste filtro.'}
              </p>
            </div>
          )}
        </div>
      </div>

      <TaskEditModal
        open={editingTaskId !== null}
        task={editingTask}
        onClose={() => setEditingTaskId(null)}
        onSave={handleSaveTask}
      />
    </div>
  )
}
