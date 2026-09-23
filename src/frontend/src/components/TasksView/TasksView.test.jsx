import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import TasksView from './TasksView'
import { fetchTasks, updateTask } from '../../lib/api'

vi.mock('../../lib/api', () => ({ fetchTasks: vi.fn(), updateTask: vi.fn() }))
vi.mock('../AgentOrb/AgentOrb', () => ({ default: () => null }))
const task = { id: '1', title: 'Revisar risco', project: 'SYN-01', priority: 'alta', done: false }
beforeEach(() => vi.resetAllMocks())

it('informa falha de leitura sem apresentar uma lista vazia como sucesso', async () => {
  fetchTasks.mockRejectedValue(new Error('rede'))
  render(<TasksView />)
  expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível carregar')
  expect(screen.queryByText('Nenhuma tarefa sugerida no momento.')).not.toBeInTheDocument()
})

it('preserva o estado da tarefa quando a gravação falha', async () => {
  fetchTasks.mockResolvedValue([task])
  updateTask.mockRejectedValue(new Error('rede'))
  render(<TasksView />)
  const button = await screen.findByRole('button', { name: 'Marcar como concluída' })
  await userEvent.click(button)
  expect(await screen.findByRole('alert')).toHaveTextContent('estado anterior')
  expect(screen.getByRole('button', { name: 'Marcar como concluída' })).toBeEnabled()
})

it('exibe a conclusão imediatamente e impede outra gravação da mesma tarefa', async () => {
  fetchTasks.mockResolvedValue([task])
  let finish
  updateTask.mockReturnValue(new Promise((resolve) => { finish = resolve }))
  render(<TasksView />)
  const button = await screen.findByRole('button', { name: 'Marcar como concluída' })
  await userEvent.click(button)
  expect(button).toBeDisabled()
  expect(button).toHaveAttribute('aria-pressed', 'true')
  await userEvent.click(button)
  expect(updateTask).toHaveBeenCalledTimes(1)
  await act(async () => finish({ ...task, done: true }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Marcar como pendente' })).toBeEnabled())
})

it('permite salvar outra tarefa e reverte somente a que falhou', async () => {
  const other = { ...task, id: '2', title: 'Revisar prazo' }
  fetchTasks.mockResolvedValue([task, other])
  let failFirst
  let finishSecond
  updateTask.mockImplementation((id) => new Promise((resolve, reject) => {
    if (id === '1') failFirst = reject
    else finishSecond = resolve
  }))
  render(<TasksView />)
  const buttons = await screen.findAllByRole('button', { name: 'Marcar como concluída' })
  await userEvent.click(buttons[0])
  expect(buttons[1]).toBeEnabled()
  await userEvent.click(buttons[1])
  expect(updateTask).toHaveBeenCalledTimes(2)
  await act(async () => finishSecond({ ...other, done: true }))
  await act(async () => failFirst(new Error('rede')))
  expect(buttons[0]).toHaveAttribute('aria-pressed', 'false')
  expect(buttons[1]).toHaveAttribute('aria-pressed', 'true')
  expect(buttons[0]).toBeEnabled()
  expect(buttons[1]).toBeEnabled()
  expect(screen.getByRole('alert')).toHaveTextContent('estado anterior')
})
