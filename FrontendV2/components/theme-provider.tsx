'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'

type Theme = 'light' | 'dark'

interface ThemeContextType {
  theme: Theme
  toggleTheme: () => void
  setTheme: (theme: Theme) => void
  collapsed: boolean
  toggleSidebar: () => void
  setCollapsed: (v: boolean) => void
}

const ThemeContext = createContext<ThemeContextType>({
  theme: 'light',
  toggleTheme: () => {},
  setTheme: () => {},
  collapsed: false,
  toggleSidebar: () => {},
  setCollapsed: () => {},
})

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>('light')
  const [collapsed, setCollapsedState] = useState(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    const stored = localStorage.getItem('bioqshield_theme') as Theme | null
    if (stored === 'light' || stored === 'dark') {
      setThemeState(stored)
      document.documentElement.classList.toggle('dark', stored === 'dark')
    } else {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      const initial = prefersDark ? 'dark' : 'light'
      setThemeState(initial)
      document.documentElement.classList.toggle('dark', prefersDark)
    }

    const storedCollapsed = localStorage.getItem('bioqshield_sidebar_collapsed')
    if (storedCollapsed !== null) {
      setCollapsedState(storedCollapsed === 'true')
    }
  }, [])

  const setTheme = (next: Theme) => {
    setThemeState(next)
    localStorage.setItem('bioqshield_theme', next)
    document.documentElement.classList.toggle('dark', next === 'dark')
  }

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark')
  }

  const setCollapsed = (v: boolean) => {
    setCollapsedState(v)
    localStorage.setItem('bioqshield_sidebar_collapsed', String(v))
  }

  const toggleSidebar = () => {
    setCollapsed(!collapsed)
  }

  return (
    <ThemeContext.Provider
      value={{
        theme,
        toggleTheme,
        setTheme,
        collapsed,
        toggleSidebar,
        setCollapsed,
      }}
    >
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  return {
    theme: ctx.theme,
    toggleTheme: ctx.toggleTheme,
    setTheme: ctx.setTheme,
  }
}

export function useSidebar() {
  const ctx = useContext(ThemeContext)
  return {
    collapsed: ctx.collapsed,
    toggleSidebar: ctx.toggleSidebar,
    setCollapsed: ctx.setCollapsed,
  }
}
