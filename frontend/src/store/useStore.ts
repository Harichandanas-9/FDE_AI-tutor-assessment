import { useState, useCallback, useEffect } from 'react'
import { Notification } from '../types'

type Theme = 'dark' | 'light'

interface StoreState {
  theme: Theme
  currentSessionId: string | null
  notifications: Notification[]
  toggleTheme: () => void
  setSessionId: (id: string | null) => void
  addNotification: (type: Notification['type'], message: string) => void
  removeNotification: (id: string) => void
}

// Global state using module-level variables + event emitter pattern
let globalTheme: Theme = (localStorage.getItem('theme') as Theme) || 'light'
let globalSessionId: string | null = null
let globalNotifications: Notification[] = []
const listeners = new Set<() => void>()

function notifyListeners() {
  listeners.forEach(fn => fn())
}

export function useStore(): StoreState {
  const [, forceUpdate] = useState(0)

  useEffect(() => {
    const listener = () => forceUpdate(n => n + 1)
    listeners.add(listener)
    return () => { listeners.delete(listener) }
  }, [])

  const toggleTheme = useCallback(() => {
    globalTheme = globalTheme === 'dark' ? 'light' : 'dark'
    localStorage.setItem('theme', globalTheme)
    notifyListeners()
  }, [])

  const setSessionId = useCallback((id: string | null) => {
    globalSessionId = id
    notifyListeners()
  }, [])

  const addNotification = useCallback((type: Notification['type'], message: string) => {
    const notification: Notification = {
      id: Date.now().toString(),
      type,
      message,
      timestamp: Date.now(),
    }
    globalNotifications = [...globalNotifications, notification]
    notifyListeners()
    // Auto-remove after 5 seconds
    setTimeout(() => {
      globalNotifications = globalNotifications.filter(n => n.id !== notification.id)
      notifyListeners()
    }, 5000)
  }, [])

  const removeNotification = useCallback((id: string) => {
    globalNotifications = globalNotifications.filter(n => n.id !== id)
    notifyListeners()
  }, [])

  return {
    theme: globalTheme,
    currentSessionId: globalSessionId,
    notifications: globalNotifications,
    toggleTheme,
    setSessionId,
    addNotification,
    removeNotification,
  }
}
