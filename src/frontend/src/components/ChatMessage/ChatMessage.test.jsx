import { render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import ChatMessage from './ChatMessage'

vi.mock('../../lib/api', () => ({
  avaliarResposta: vi.fn(),
  generateSpeech: vi.fn(),
}))

vi.mock('../AgentOrb/AgentOrb', () => ({
  default: () => <span data-testid="agent-avatar" />,
}))

it('exibe a resposta do agente dentro de um balão visual', () => {
  render(<ChatMessage role="agent" content="Aqui está a resposta solicitada." />)

  const bubble = screen.getByTestId('agent-message-bubble')
  expect(bubble).toHaveTextContent('Aqui está a resposta solicitada.')
  expect(bubble).toHaveClass('rounded-2xl', 'border', 'bg-surface/95', 'px-4', 'py-3')
  expect(screen.getByTestId('agent-avatar')).toBeInTheDocument()
})

it('mantém o balão do usuário visualmente distinto', () => {
  render(<ChatMessage role="user" content="Minha pergunta" />)

  const bubble = screen.getByTestId('user-message-bubble')
  expect(bubble).toHaveClass('rounded-tr-md')
  expect(bubble).not.toHaveClass('rounded-tl-md')
})
