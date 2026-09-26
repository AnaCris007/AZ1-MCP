import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import CalendarGridView from './CalendarGridView'

const DEZEMBRO_2026 = new Date(2026, 11, 1)

it('renderiza 42 células, seis semanas começando na segunda-feira', () => {
  const { container } = render(
    <CalendarGridView visibleMonth={DEZEMBRO_2026} onPrevMonth={() => {}} onNextMonth={() => {}} days={[]} onDeleteEvent={() => {}} />
  )
  // 7 cabeçalhos de dia da semana + 42 células do mês.
  const celulas = container.querySelectorAll('.grid.grid-cols-7')[1].children
  expect(celulas).toHaveLength(42)
})

it('coloca um evento na célula do dia certo, casando pelo campo iso', () => {
  const days = [
    {
      date: '5 de dezembro',
      weekday: 'sábado',
      iso: '2026-12-05',
      events: [{ id: 'evento-7', title: 'Dentista', type: 'evento', project: '', time: '14:00' }],
    },
  ]
  render(
    <CalendarGridView visibleMonth={DEZEMBRO_2026} onPrevMonth={() => {}} onNextMonth={() => {}} days={days} onDeleteEvent={() => {}} />
  )
  expect(screen.getByText('Dentista')).toBeInTheDocument()
})

it('navega entre meses ao clicar em anterior/próximo', async () => {
  const onPrevMonth = vi.fn()
  const onNextMonth = vi.fn()
  render(
    <CalendarGridView visibleMonth={DEZEMBRO_2026} onPrevMonth={onPrevMonth} onNextMonth={onNextMonth} days={[]} onDeleteEvent={() => {}} />
  )
  await userEvent.click(screen.getByRole('button', { name: 'Próximo mês' }))
  await userEvent.click(screen.getByRole('button', { name: 'Mês anterior' }))
  expect(onNextMonth).toHaveBeenCalledTimes(1)
  expect(onPrevMonth).toHaveBeenCalledTimes(1)
})

it('excluir um evento na grade chama o handler com o id composto', async () => {
  const onDeleteEvent = vi.fn()
  const days = [
    {
      date: '5 de dezembro',
      weekday: 'sábado',
      iso: '2026-12-05',
      events: [{ id: 'evento-7', title: 'Dentista', type: 'evento', project: '', time: '14:00' }],
    },
  ]
  render(
    <CalendarGridView visibleMonth={DEZEMBRO_2026} onPrevMonth={() => {}} onNextMonth={() => {}} days={days} onDeleteEvent={onDeleteEvent} />
  )
  await userEvent.click(screen.getByRole('button', { name: 'Excluir Dentista' }))
  expect(onDeleteEvent).toHaveBeenCalledWith('evento-7')
})

it('não mostra botão de excluir em marco/prazo', () => {
  const days = [
    {
      date: '5 de dezembro',
      weekday: 'sábado',
      iso: '2026-12-05',
      events: [{ id: 'marco-SYN-01', title: 'Término previsto', type: 'marco', project: 'SYN-01', time: '' }],
    },
  ]
  render(
    <CalendarGridView visibleMonth={DEZEMBRO_2026} onPrevMonth={() => {}} onNextMonth={() => {}} days={days} onDeleteEvent={() => {}} />
  )
  expect(screen.queryByRole('button', { name: 'Excluir Término previsto' })).not.toBeInTheDocument()
})
