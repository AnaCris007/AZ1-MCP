import { motion } from 'framer-motion'
import Logo from '../Logo/Logo'

const STATE_CONFIG = {
  idle: {
    scale: [1, 1.03, 1],
    duration: 4,
  },
  listening: {
    scale: [1, 1.12, 1],
    duration: 1.2,
  },
  processing: {
    scale: [1, 1.06, 1],
    duration: 0.9,
  },
}

export default function AgentOrb({ state = 'idle', size = 84 }) {
  const config = STATE_CONFIG[state] ?? STATE_CONFIG.idle

  return (
    <div
      className="relative flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      <motion.div
        className="flex items-center justify-center"
        animate={{ scale: config.scale }}
        transition={{
          duration: config.duration,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      >
        <Logo size={size} />
      </motion.div>
      {state === 'listening' && (
        <motion.div
          className="absolute inset-0 rounded-full border border-[#1A55B5]/40"
          animate={{ scale: [1, 1.5, 1.9], opacity: [0.5, 0.2, 0] }}
          transition={{ duration: 1.4, repeat: Infinity, ease: 'easeOut' }}
        />
      )}
      {state === 'processing' && (
        <div className="absolute -bottom-6 flex items-center gap-1">
          {[0, 1, 2].map((i) => (
            <motion.span
              key={i}
              className="h-1.5 w-1.5 rounded-full bg-text-muted"
              animate={{ opacity: [0.25, 1, 0.25] }}
              transition={{
                duration: 1,
                repeat: Infinity,
                delay: i * 0.15,
                ease: 'easeInOut',
              }}
            />
          ))}
        </div>
      )}
    </div>
  )
}
