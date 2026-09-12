import { motion } from 'framer-motion'
import { Calendar, Check, ListChecks, Pencil, Sparkles } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import AgentOrb from '../AgentOrb/AgentOrb'
import { fetchTasks, updateTask } from '../../lib/api'
import TaskEditModal from './TaskEditModal'

const PRIORITY_ORDER = { alta: 0, media: 1, baixa: 2 }

const PRIORITY_STYLES = {
  alta: 'bg-red-500/10 text-red-500 dark:text-red-400',
  media: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
  baixa: 'bg-emerald-500/10 text-emerald-500 dark:text-emerald-400',
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

export default function TasksView() {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [savingIds, setSavingIds] = useState(new Set())
  const pendingUpdates = useRef(new Set())
  const [error, setError] = useState('')
  const [editingTaskId, setEditingTaskId] = useState(null)

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
    <div className="flex-1 overflow-y-auto px-4 pb-10 pt-6">
      <div className="mx-auto flex w-full max-w-[720px] flex-col">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <ListChecks size={20} strokeWidth={1.75} className="text-text-primary" />
            <h1 className="text-[18px] font-semibold text-text-primary">Tarefas</h1>
          </div>
          <span className="flex items-center gap-1.5 rounded-full border border-border-soft px-3 py-1 text-[12px] font-medium text-text-muted">
            <Sparkles size={12} strokeWidth={1.75} />
            Sugeridas pelo agente
          </span>
        </div>

        {loading && <p role="status">Carregando tarefas...</p>}
        {savingIds.size > 0 && <p role="status">Salvando alterações...</p>}
        {error && <p role="alert">{error}</p>}
        <div className="flex flex-col gap-2">
          {sortedTasks.map((task, index) => (
            <motion.div
              key={task.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2, delay: index * 0.03, ease: 'easeOut' }}
              className={`flex items-start gap-3 rounded-xl border border-border-soft bg-surface px-4 py-3 transition-opacity ${
                task.done ? 'opacity-50' : ''
              }`}
            >
              <button
                type="button"
                onClick={() => toggleTask(task.id)}
                disabled={savingIds.has(task.id)}
                aria-label={task.done ? 'Marcar como pendente' : 'Marcar como concluída'}
                aria-pressed={task.done}
                className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors ${
                  task.done
                    ? 'border-button-primary bg-button-primary text-button-primary-text'
                    : 'border-border text-transparent hover:border-text-secondary'
                }`}
              >
                <Check size={12} strokeWidth={2.5} />
              </button>

              <div className="min-w-0 flex-1">
                <p
                  className={`text-[14px] font-medium text-text-primary ${
                    task.done ? 'line-through' : ''
                  }`}
                >
                  {task.title}
                </p>
                {task.description && (
                  <p className="mt-1 text-[13px] leading-relaxed text-text-secondary">
                    {task.description}
                  </p>
                )}
                <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px] text-text-muted">
                  <span className="truncate">{task.project}</span>
                  {task.dueDate && (
                    <span className="flex items-center gap-1">
                      <Calendar size={11} strokeWidth={1.75} />
                      {formatDueDate(task.dueDate)}
                    </span>
                  )}
                </div>
              </div>

              <div className="flex shrink-0 items-center gap-2">
                <span
                  className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${PRIORITY_STYLES[task.priority]}`}
                >
                  {PRIORITY_LABELS[task.priority]}
                </span>
                <button
                  type="button"
                  onClick={() => setEditingTaskId(task.id)}
                  disabled={savingIds.has(task.id)}
                  aria-label="Editar tarefa"
                  className="flex h-7 w-7 items-center justify-center rounded-lg text-text-muted transition-colors hover:bg-black/5 hover:text-text-primary dark:hover:bg-white/10"
                >
                  <Pencil size={13} strokeWidth={1.75} />
                </button>
              </div>
            </motion.div>
          ))}

          {!loading && !error && sortedTasks.length === 0 && (
            <div className="flex flex-col items-center gap-3 py-16">
              <AgentOrb state="idle" size={40} />
              <p className="text-[13px] text-text-muted">
                Nenhuma tarefa sugerida no momento.
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
