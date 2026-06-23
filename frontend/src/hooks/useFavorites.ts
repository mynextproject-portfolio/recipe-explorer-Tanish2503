import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { authApi } from '../services/authApi'
import { useAuth } from '../contexts/AuthContext'

export function useFavorites() {
  const { user } = useAuth()
  return useQuery({
    queryKey: ['favorites', user?.id],
    queryFn: () => authApi.getFavorites(),
    enabled: !!user,
  })
}

export function useIsFavorite(recipeId: string, source: string) {
  const { data: favs } = useFavorites()
  return (favs ?? []).some(f => f.recipe_id === recipeId && f.recipe_source === source)
}

export function useToggleFavorite(recipeId: string, source: string) {
  const { user } = useAuth()
  const qc = useQueryClient()
  const isFav = useIsFavorite(recipeId, source)

  const add = useMutation({
    mutationFn: () => authApi.addFavorite(recipeId, source),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['favorites'] }),
  })

  const remove = useMutation({
    mutationFn: () => authApi.removeFavorite(recipeId, source),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['favorites'] }),
  })

  const toggle = () => {
    if (!user) return
    isFav ? remove.mutate() : add.mutate()
  }

  return {
    isFavorite: isFav,
    toggle,
    isLoading: add.isPending || remove.isPending,
    isAuthenticated: !!user,
  }
}
