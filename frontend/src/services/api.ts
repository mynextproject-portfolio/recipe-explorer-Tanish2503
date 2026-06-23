import type { Recipe, RecipeFormData, RecipeSearchResponse } from '../types/recipe'

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  getRecipes: (search?: string): Promise<RecipeSearchResponse> => {
    const qs = search ? `?search=${encodeURIComponent(search)}` : ''
    return request<RecipeSearchResponse>(`/recipes${qs}`)
  },

  getRecipe: (id: string): Promise<Recipe> =>
    request<Recipe>(`/recipes/${id}`),

  getExternalRecipe: (id: string): Promise<Recipe> =>
    request<Recipe>(`/recipes/external/${id}`),

  createRecipe: (data: RecipeFormData): Promise<Recipe> =>
    request<Recipe>('/recipes', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateRecipe: (id: string, data: RecipeFormData): Promise<Recipe> =>
    request<Recipe>(`/recipes/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteRecipe: (id: string): Promise<{ message: string }> =>
    request<{ message: string }>(`/recipes/${id}`, { method: 'DELETE' }),
}
