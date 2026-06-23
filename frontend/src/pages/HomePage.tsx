import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, AlertCircle } from 'lucide-react'
import { useRecipes } from '../hooks/useRecipes'
import { useDebounce } from '../hooks/useDebounce'
import { RecipeCard } from '../components/RecipeCard'
import { SkeletonCard } from '../components/SkeletonCard'
import { SearchBar } from '../components/SearchBar'

export function HomePage() {
  const [query, setQuery] = useState('')
  const debouncedQuery = useDebounce(query, 350)
  const isSearching = query !== debouncedQuery

  const { data, isLoading, error } = useRecipes(debouncedQuery || undefined)

  const recipes = data?.recipes ?? []

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      {/* Hero */}
      {!debouncedQuery && !isLoading && (
        <div className="mb-10 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-neutral-100 sm:text-5xl">
            Discover{' '}
            <span className="text-amber-400">delicious</span> recipes
          </h1>
          <p className="mt-3 text-base text-neutral-400 max-w-xl mx-auto">
            Search your personal collection or explore thousands of dishes from TheMealDB in real time.
          </p>
        </div>
      )}

      {/* Search */}
      <div className="mb-8">
        <SearchBar
          value={query}
          onChange={setQuery}
          isSearching={isSearching || (isLoading && !!query)}
          resultCount={debouncedQuery ? recipes.length : undefined}
        />

        {data?.external_search_error && (
          <div className="mt-3 flex items-center gap-2 rounded-lg border border-yellow-500/20 bg-yellow-500/10 px-3 py-2 text-xs text-yellow-400">
            <AlertCircle size={14} />
            TheMealDB unavailable — showing collection results only
          </div>
        )}
      </div>

      {/* Timing badge */}
      {data?.timing && debouncedQuery && (
        <div className="mb-4 flex gap-3 text-xs text-neutral-600">
          <span>Internal: {data.timing.internal_ms}ms</span>
          {data.timing.external_ms !== undefined && (
            <span>TheMealDB: {data.timing.external_ms}ms</span>
          )}
        </div>
      )}

      {/* Grid */}
      {isLoading || isSearching ? (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : error ? (
        <div className="flex flex-col items-center gap-3 py-20 text-center">
          <AlertCircle size={32} className="text-red-400" />
          <p className="text-neutral-400">Failed to load recipes</p>
          <p className="text-sm text-neutral-600">{(error as Error).message}</p>
        </div>
      ) : recipes.length === 0 ? (
        <div className="flex flex-col items-center gap-4 py-20 text-center">
          <span className="text-5xl">🍽️</span>
          <h3 className="text-lg font-medium text-neutral-300">
            {debouncedQuery ? `No recipes found for "${debouncedQuery}"` : 'No recipes yet'}
          </h3>
          <p className="text-sm text-neutral-500">
            {debouncedQuery
              ? 'Try a different search term'
              : 'Add your first recipe to get started'}
          </p>
          {!debouncedQuery && (
            <Link
              to="/recipes/new"
              className="mt-2 flex items-center gap-2 rounded-xl bg-amber-500 px-5 py-2.5 text-sm font-semibold text-black hover:bg-amber-400 transition-colors"
            >
              <Plus size={16} /> Add Recipe
            </Link>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 fade-in">
          {recipes.map(recipe => (
            <RecipeCard key={`${recipe.source}-${recipe.id}`} recipe={recipe} />
          ))}
        </div>
      )}

      {/* Count */}
      {recipes.length > 0 && !isLoading && (
        <p className="mt-8 text-center text-xs text-neutral-600">
          {recipes.length} recipe{recipes.length !== 1 ? 's' : ''} shown
        </p>
      )}
    </div>
  )
}
