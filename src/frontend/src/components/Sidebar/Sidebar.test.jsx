import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import Sidebar from './Sidebar'

it('oferece configurações no rodapé da barra lateral', async () => {
  const onConfig = vi.fn()
  render(
    <Sidebar
      collapsed={false}
      onToggle={() => {}}
      conversations={[]}
      activeId={null}
      onSelectConversation={() => {}}
      onNewConversation={() => {}}
      onConfig={onConfig}
    />,
  )

  await userEvent.click(screen.getByRole('button', { name: 'Configurações' }))
  expect(onConfig).toHaveBeenCalledTimes(1)
})
