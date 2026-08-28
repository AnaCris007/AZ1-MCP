import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'az1-theme'

function getInitialMode() {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'dark' || stored === 'light' || stored === 'system') return stored
  return 'system'
}

function systemPrefersDark() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

export function useTheme() {
  const [mode, setMode] = useState(getInitialMode)
  const [systemDark, setSystemDark] = useState(systemPrefersDark)

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = (event) => setSystemDark(event.matches)
    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])

  const theme = mode === 'system' ? (systemDark ? 'dark' : 'light') : mode

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem(STORAGE_KEY, mode)
  }, [theme, mode])

  const toggleTheme = useCallback(() => {
    setMode(theme === 'dark' ? 'light' : 'dark')
  }, [theme])

  return { theme, mode, setMode, toggleTheme }
}
