import { useRef } from 'react'

const BAR_COUNT = 28
const MIN_HEIGHT = 4
const MAX_HEIGHT = 26

export default function Waveform({ volume = 0 }) {
  const weightsRef = useRef(
    Array.from({ length: BAR_COUNT }, () => 0.45 + Math.random() * 0.55),
  )

  return (
    <div className="flex h-8 flex-1 items-center justify-center gap-[3px] overflow-hidden">
      {weightsRef.current.map((weight, index) => {
        const height = Math.max(
          MIN_HEIGHT,
          Math.min(MAX_HEIGHT, volume * weight * MAX_HEIGHT),
        )
        return (
          <span
            key={index}
            className="w-[2.5px] shrink-0 rounded-full bg-[#1c5ca2]"
            style={{
              height,
              transition: 'height 90ms ease-out',
              opacity: 0.4 + weight * 0.5,
            }}
          />
        )
      })}
    </div>
  )
}
