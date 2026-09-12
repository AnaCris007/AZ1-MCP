import { render, screen } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import CalendarView from './CalendarView'
import { fetchCalendarEvents } from '../../lib/api'

vi.mock('../../lib/api', () => ({ fetchCalendarEvents: vi.fn() }))
beforeEach(() => vi.resetAllMocks())

it('distingue falha de carregamento de uma agenda vazia', async () => {
  fetchCalendarEvents.mockRejectedValue(new Error('rede'))
  render(<CalendarView />)
  expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível carregar a agenda')
  expect(screen.queryByText('Nenhum marco ou prazo registrado.')).not.toBeInTheDocument()
})

it('informa quando a consulta retorna sem eventos', async () => {
  fetchCalendarEvents.mockResolvedValue({ days: [] })
  render(<CalendarView />)
  expect(await screen.findByText('Nenhum marco ou prazo registrado.')).toBeInTheDocument()
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
})
