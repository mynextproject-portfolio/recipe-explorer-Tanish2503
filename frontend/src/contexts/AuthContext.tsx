import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react'
import { authApi, getStoredToken } from '../services/authApi'
import type { User } from '../types/auth'

interface AuthContextValue {
  user: User | null
  token: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(() => getStoredToken())
  const [isLoading, setIsLoading] = useState(!!getStoredToken())

  // Rehydrate user from stored token on mount
  useEffect(() => {
    if (!token) { setIsLoading(false); return }
    authApi.me()
      .then(setUser)
      .catch(() => {
        localStorage.removeItem('token')
        setToken(null)
      })
      .finally(() => setIsLoading(false))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const _store = useCallback((tok: string, u: User) => {
    localStorage.setItem('token', tok)
    setToken(tok)
    setUser(u)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const data = await authApi.login(email, password)
    _store(data.access_token, data.user)
  }, [_store])

  const register = useCallback(async (email: string, username: string, password: string) => {
    const data = await authApi.register(email, username, password)
    _store(data.access_token, data.user)
  }, [_store])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
