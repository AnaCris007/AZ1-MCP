import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import TopBar from './TopBar'

const { signOut } = vi.hoisted(() => ({ signOut: vi.fn() }))

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { email: 'usuario@az1.com.br' }, signOut }),
}))

beforeEach(() => signOut.mockReset())

function renderTopBar() {
  return render(
    <TopBar
      title="AZ1"
      onShare={() => {}}
      onNewChat={() => {}}
      theme="light"
      onToggleTheme={() => {}}
    />,
  )
}

it('mostra o e-mail e a ação de sair somente após abrir o perfil', async () => {
  renderTopBar()
  expect(screen.queryByText('usuario@az1.com.br')).not.toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: 'Abrir menu do perfil' }))
  expect(screen.getByText('usuario@az1.com.br')).toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: 'Sair' }))
  expect(signOut).toHaveBeenCalledTimes(1)
})

it('fecha o menu do perfil ao pressionar Escape', async () => {
  renderTopBar()
  await userEvent.click(screen.getByRole('button', { name: 'Abrir menu do perfil' }))
  await userEvent.keyboard('{Escape}')
  await waitFor(() => expect(screen.queryByText('usuario@az1.com.br')).not.toBeInTheDocument())
})
