import { useEffect, useState } from 'react'

const STORAGE_KEY = 'az1-settings'

const DEFAULTS = {
  startSidebarCollapsed: false,
}

function getInitialSettings() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY))
    return { ...DEFAULTS, ...stored }
  } catch {
    return DEFAULTS
  }
}

export function useSettings() {
  const [settings, setSettings] = useState(getInitialSettings)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
  }, [settings])

  const updateSetting = (key, value) =>
    setSettings((prev) => ({ ...prev, [key]: value }))

  return { settings, updateSetting }
}
