import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import type { RecipeFormData } from '../types/recipe'

export function useRecipes(search?: string) {
  return useQuery({
    queryKey: ['recipes', search],
    queryFn: () => api.getRecipes(search || undefined),
  })
}

export function useRecipe(id: string, source: 'internal' | 'external') {
  return useQuery({
    queryKey: ['recipe', id, source],
    queryFn: () =>
      source === 'external' ? api.getExternalRecipe(id) : api.getRecipe(id),
    enabled: !!id,
  })
}

export function useCreateRecipe() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: RecipeFormData) => api.createRecipe(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['recipes'] }),
  })
}

export function useUpdateRecipe(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: RecipeFormData) => api.updateRecipe(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['recipes'] })
      qc.invalidateQueries({ queryKey: ['recipe', id] })
    },
  })
}

export function useDeleteRecipe() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.deleteRecipe(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['recipes'] }),
  })
}
