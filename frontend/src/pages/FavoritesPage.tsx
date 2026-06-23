import { Link } from 'react-router-dom'
import { Heart, AlertCircle } from 'lucide-react'
import { useFavorites } from '../hooks/useFavorites'
import { useRecipes } from '../hooks/useRecipes'
import { RecipeCard } from '../components/RecipeCard'
import { SkeletonCard } from '../components/SkeletonCard'
import type { Recipe } from '../types/recipe'

function FavoriteRecipeCard({ recipeId, source }: { recipeId: string; source: string }) {
  const { data, isLoading } = useRecipes()
  if (isLoading) return <SkeletonCard />

  // For internal recipes, find in the recipe list
  if (source === 'internal') {
    const recipe = data?.recipes.find(r => r.id === recipeId && r.source === 'internal')
    if (!recipe) return null
    return <RecipeCard recipe={recipe} />
  }

  // For external, show a minimal placeholder card linking to the detail
  const placeholder: Recipe = {
    id: recipeId,
    title: `External Recipe #${recipeId}`,
    description: 'Saved from TheMealDB',
    cuisine: '',
    ingredients: [],
    instructions: [],
    tags: [],
    source: 'external',
  }
  return <RecipeCard recipe={placeholder} />
}

export function FavoritesPage() {
  const { data: favs, isLoading, error } = useFavorites()

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-8 flex items-center gap-3">
        <Heart size={22} className="text-red-400" />
        <h1 className="text-2xl font-bold text-neutral-100">My Favorites</h1>
        {favs && (
          <span className="rounded-full bg-neutral-800 px-2.5 py-0.5 text-xs text-neutral-400">
            {favs.length}
          </span>
        )}
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : error ? (
        <div className="flex flex-col items-center gap-3 py-20 text-center">
          <AlertCircle size={32} className="text-red-400" />
          <p className="text-neutral-400">Failed to load favorites</p>
        </div>
      ) : !favs?.length ? (
        <div className="flex flex-col items-center gap-4 py-20 text-center">
          <Heart size={40} className="text-neutral-700" />
          <h3 className="text-lg font-medium text-neutral-300">No favorites yet</h3>
          <p className="text-sm text-neutral-500">
            Tap the heart icon on any recipe to save it here
          </p>
          <Link
            to="/"
            className="mt-2 rounded-xl bg-amber-500 px-5 py-2.5 text-sm font-semibold text-black hover:bg-amber-400 transition-colors"
          >
            Browse Recipes
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 fade-in">
          {favs.map(f => (
            <FavoriteRecipeCard key={f.id} recipeId={f.recipe_id} source={f.recipe_source} />
          ))}
        </div>
      )}
    </div>
  )
}
