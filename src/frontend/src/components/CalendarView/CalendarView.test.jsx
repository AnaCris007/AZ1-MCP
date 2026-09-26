import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import CalendarView from './CalendarView'
import { createCalendarEvent, deleteCalendarEvent, fetchCalendarEvents } from '../../lib/api'

vi.mock('../../lib/api', () => ({
  fetchCalendarEvents: vi.fn(),
  createCalendarEvent: vi.fn(),
  deleteCalendarEvent: vi.fn(),
}))
beforeEach(() => vi.resetAllMocks())

it('distingue falha de carregamento de uma agenda vazia', async () => {
  fetchCalendarEvents.mockRejectedValue(new Error('rede'))
  render(<CalendarView />)
  expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível carregar a agenda')
  expect(screen.queryByText('Nenhum marco, prazo ou evento registrado.')).not.toBeInTheDocument()
})

it('informa quando a consulta retorna sem eventos', async () => {
  fetchCalendarEvents.mockResolvedValue({ days: [] })
  render(<CalendarView />)
  expect(await screen.findByText('Nenhum marco, prazo ou evento registrado.')).toBeInTheDocument()
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
})

it('renderiza um evento local com pílula própria', async () => {
  fetchCalendarEvents.mockResolvedValue({
    days: [
      {
        date: '5 de dezembro',
        weekday: 'sábado',
        iso: '2026-12-05',
        events: [{ id: 'evento-7', title: 'Dentista', type: 'evento', project: '', time: '14:00' }],
      },
    ],
  })
  render(<CalendarView />)
  expect(await screen.findByText('Dentista')).toBeInTheDocument()
  expect(screen.getByText('Evento')).toBeInTheDocument()
})

it('abre os detalhes de um marco ao clicar no item', async () => {
  fetchCalendarEvents.mockResolvedValue({
    days: [
      {
        date: '5 de dezembro',
        weekday: 'sábado',
        iso: '2026-12-05',
        events: [{
          id: 'marco-SYN-01',
          title: 'Término previsto — Implantação',
          type: 'marco',
          project: 'SYN-01',
          time: '',
          description: 'Fase: Execução',
          responsible: 'Ana Silva',
          status: 'Em andamento',
        }],
      },
    ],
  })

  render(<CalendarView />)
  await userEvent.click(await screen.findByRole('button', { name: /Término previsto/ }))

  expect(screen.getByRole('dialog', { name: 'Término previsto — Implantação' })).toBeInTheDocument()
  expect(screen.getByText('Ana Silva')).toBeInTheDocument()
  expect(screen.getByText('Fase: Execução')).toBeInTheDocument()
})

it('mostra o botão de excluir só em eventos próprios', async () => {
  fetchCalendarEvents.mockResolvedValue({
    days: [
      {
        date: '5 de dezembro',
        weekday: 'sábado',
        iso: '2026-12-05',
        events: [
          { id: 'marco-SYN-01', title: 'Término previsto', type: 'marco', project: 'SYN-01', time: '' },
          { id: 'evento-7', title: 'Dentista', type: 'evento', project: '', time: '14:00' },
        ],
      },
    ],
  })
  render(<CalendarView />)
  await screen.findByText('Dentista')
  expect(screen.getByRole('button', { name: 'Excluir Dentista' })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Excluir Término previsto' })).not.toBeInTheDocument()
})

it('exclui um evento local otimisticamente e chama a API', async () => {
  fetchCalendarEvents.mockResolvedValue({
    days: [
      {
        date: '5 de dezembro',
        weekday: 'sábado',
        iso: '2026-12-05',
        events: [{ id: 'evento-7', title: 'Dentista', type: 'evento', project: '', time: '14:00' }],
      },
    ],
  })
  deleteCalendarEvent.mockResolvedValue()
  render(<CalendarView />)
  const botao = await screen.findByRole('button', { name: 'Excluir Dentista' })
  await userEvent.click(botao)
  expect(deleteCalendarEvent).toHaveBeenCalledWith('7')
  expect(screen.queryByText('Dentista')).not.toBeInTheDocument()
})

it('restaura somente o evento cuja exclusão falhou e permite tentar novamente', async () => {
  fetchCalendarEvents.mockResolvedValue({
    days: [
      {
        date: '5 de dezembro',
        weekday: 'sábado',
        iso: '2026-12-05',
        events: [
          { id: 'evento-7', title: 'Dentista', type: 'evento', project: '', time: '14:00' },
          { id: 'evento-8', title: 'Reunião', type: 'evento', project: '', time: '15:00' },
        ],
      },
    ],
  })
  deleteCalendarEvent
    .mockRejectedValueOnce(new Error('rede'))
    .mockResolvedValueOnce()
  render(<CalendarView />)

  await userEvent.click(await screen.findByRole('button', { name: 'Excluir Dentista' }))

  expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível excluir o evento')
  expect(screen.getByText('Dentista')).toBeInTheDocument()
  expect(screen.getByText('Reunião')).toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: 'Excluir Dentista' }))
  await waitFor(() => expect(screen.queryByText('Dentista')).not.toBeInTheDocument())
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  expect(screen.getByText('Reunião')).toBeInTheDocument()
})

it('distingue na lista o mesmo dia e mês em anos diferentes', async () => {
  fetchCalendarEvents.mockResolvedValue({
    days: [
      {
        date: '5 de dezembro',
        weekday: 'sábado',
        iso: '2026-12-05',
        events: [{ id: 'evento-7', title: 'Evento 2026', type: 'evento', project: '', time: '' }],
      },
      {
        date: '5 de dezembro',
        weekday: 'domingo',
        iso: '2027-12-05',
        events: [{ id: 'evento-8', title: 'Evento 2027', type: 'evento', project: '', time: '' }],
      },
    ],
  })

  render(<CalendarView />)

  expect(await screen.findByText('5 de dezembro de 2026')).toBeInTheDocument()
  expect(screen.getByText('5 de dezembro de 2027')).toBeInTheDocument()
  expect(screen.getByText('Evento 2026')).toBeInTheDocument()
  expect(screen.getByText('Evento 2027')).toBeInTheDocument()
})

it('abre o modal, cria um evento e recarrega a agenda', async () => {
  fetchCalendarEvents.mockResolvedValue({ days: [] })
  createCalendarEvent.mockResolvedValue({ id: 1, title: 'Dentista', date: '2026-12-05', time: '', description: '' })
  render(<CalendarView />)
  await screen.findByText('Nenhum marco, prazo ou evento registrado.')

  await userEvent.click(screen.getByRole('button', { name: /Novo evento/i }))
  await userEvent.type(screen.getByLabelText('Título'), 'Dentista')
  await userEvent.type(screen.getByLabelText('Data'), '2026-12-05')
  await userEvent.click(screen.getByRole('button', { name: 'Criar' }))

  expect(createCalendarEvent).toHaveBeenCalledWith({ title: 'Dentista', date: '2026-12-05', time: '', description: '' })
  expect(fetchCalendarEvents).toHaveBeenCalledTimes(2)
})

it('fecha o modal de criação ao clicar fora, mas não ao clicar no conteúdo', async () => {
  fetchCalendarEvents.mockResolvedValue({ days: [] })
  render(<CalendarView />)
  await screen.findByText('Nenhum marco, prazo ou evento registrado.')

  await userEvent.click(screen.getByRole('button', { name: /Novo evento/i }))
  await userEvent.click(screen.getByRole('dialog', { name: 'Novo evento' }))
  expect(screen.getByRole('dialog', { name: 'Novo evento' })).toBeInTheDocument()

  await userEvent.click(screen.getByTestId('create-event-modal-layer'))
  await waitFor(() => {
    expect(screen.queryByRole('dialog', { name: 'Novo evento' })).not.toBeInTheDocument()
  })
})

it('fecha os detalhes ao clicar fora, mas não ao clicar no conteúdo', async () => {
  fetchCalendarEvents.mockResolvedValue({
    days: [
      {
        date: '5 de dezembro',
        weekday: 'sábado',
        iso: '2026-12-05',
        events: [{ id: 'evento-7', title: 'Dentista', type: 'evento', project: '', time: '14:00' }],
      },
    ],
  })
  render(<CalendarView />)

  const item = (await screen.findByText('Dentista')).closest('[role="button"]')
  await userEvent.click(item)
  await userEvent.click(screen.getByRole('dialog', { name: 'Dentista' }))
  expect(screen.getByRole('dialog', { name: 'Dentista' })).toBeInTheDocument()

  await userEvent.click(screen.getByTestId('event-details-modal-layer'))
  await waitFor(() => {
    expect(screen.queryByRole('dialog', { name: 'Dentista' })).not.toBeInTheDocument()
  })
})

it('alterna entre a visualização em lista e em grade', async () => {
  fetchCalendarEvents.mockResolvedValue({ days: [] })
  render(<CalendarView />)
  await screen.findByText('Nenhum marco, prazo ou evento registrado.')

  await userEvent.click(screen.getByRole('button', { name: 'Mês' }))
  expect(await screen.findByRole('button', { name: 'Próximo mês' })).toBeInTheDocument()
})
