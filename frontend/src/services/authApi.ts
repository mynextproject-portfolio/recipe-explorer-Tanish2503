import type { AuthResponse, Favorite, User } from '../types/auth'

const BASE = '/api/auth'

export function getStoredToken(): string | null {
  return localStorage.getItem('token')
}

export function getAuthHeader(): Record<string, string> {
  const token = getStoredToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function authRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
      ...init?.headers,
    },
    ...init,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const authApi = {
  register: (email: string, username: string, password: string): Promise<AuthResponse> =>
    authRequest('/register', {
      method: 'POST',
      body: JSON.stringify({ email, username, password }),
    }),

  login: (email: string, password: string): Promise<AuthResponse> =>
    authRequest('/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  me: (): Promise<User> => authRequest('/me'),

  getFavorites: (): Promise<Favorite[]> => authRequest('/favorites'),

  addFavorite: (recipeId: string, source: string): Promise<Favorite> =>
    authRequest(`/favorites/${recipeId}?source=${source}`, { method: 'POST' }),

  removeFavorite: (recipeId: string, source: string): Promise<void> =>
    authRequest(`/favorites/${recipeId}?source=${source}`, { method: 'DELETE' }),
}
