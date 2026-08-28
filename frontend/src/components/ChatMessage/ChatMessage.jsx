import { motion } from 'framer-motion'
import AgentOrb from '../AgentOrb/AgentOrb'

export default function ChatMessage({ role, content }) {
  const isUser = role === 'user'

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className={`flex w-full gap-3 py-4 ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      {!isUser && (
        <div className="mt-0.5 shrink-0">
          <AgentOrb size={28} state="idle" />
        </div>
      )}
      <div
        className={`max-w-[640px] text-[15px] leading-relaxed ${
          isUser
            ? 'rounded-2xl bg-surface px-4 py-3 text-text-primary'
            : 'text-text-primary'
        }`}
      >
        {content}
      </div>
    </motion.div>
  )
}
