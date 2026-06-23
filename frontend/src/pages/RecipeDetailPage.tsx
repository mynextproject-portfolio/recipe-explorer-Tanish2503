import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, Edit2, Trash2, CheckCircle2, ChefHat, AlertCircle } from 'lucide-react'
import { useRecipe, useDeleteRecipe } from '../hooks/useRecipes'
import { SourceBadge } from '../components/SourceBadge'

const FALLBACK_IMAGES = [
  'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800&h=400&fit=crop',
  'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800&h=400&fit=crop',
  'https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=800&h=400&fit=crop',
]

function getFallbackImage(id: string) {
  let h = 0
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0
  return FALLBACK_IMAGES[h % FALLBACK_IMAGES.length]
}

export function RecipeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isExternal = location.pathname.includes('/external/')

  const { data: recipe, isLoading, error } = useRecipe(
    id!,
    isExternal ? 'external' : 'internal'
  )
  const deleteMutation = useDeleteRecipe()

  const handleDelete = async () => {
    if (!confirm('Delete this recipe?')) return
    await deleteMutation.mutateAsync(id!)
    navigate('/')
  }

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <div className="skeleton h-6 w-32 mb-6" />
        <div className="skeleton h-72 w-full rounded-xl mb-6" />
        <div className="skeleton h-8 w-2/3 mb-3" />
        <div className="skeleton h-4 w-full mb-2" />
        <div className="skeleton h-4 w-5/6" />
      </div>
    )
  }

  if (error || !recipe) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-20 text-center">
        <AlertCircle size={40} className="mx-auto mb-4 text-red-400" />
        <h2 className="text-xl font-semibold text-neutral-200 mb-2">Recipe not found</h2>
        <p className="text-sm text-neutral-500 mb-6">{(error as Error)?.message}</p>
        <Link to="/" className="text-sm text-amber-400 hover:text-amber-300">
          ← Back to all recipes
        </Link>
      </div>
    )
  }

  const img = recipe.image || getFallbackImage(recipe.id)

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 fade-in">
      {/* Back */}
      <Link
        to="/"
        className="mb-6 flex items-center gap-1.5 text-sm text-neutral-400 hover:text-neutral-200 transition-colors w-fit"
      >
        <ArrowLeft size={16} /> All recipes
      </Link>

      {/* Hero image */}
      <div className="mb-6 h-64 sm:h-80 overflow-hidden rounded-2xl bg-[#141414]">
        <img
          src={img}
          alt={recipe.title}
          className="h-full w-full object-cover"
          onError={e => { e.currentTarget.src = FALLBACK_IMAGES[0] }}
        />
      </div>

      {/* Header */}
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <SourceBadge source={recipe.source} />
            {recipe.cuisine && (
              <span className="text-xs text-amber-400 font-medium uppercase tracking-wide">
                {recipe.cuisine}
              </span>
            )}
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-neutral-100 leading-tight">
            {recipe.title}
          </h1>
          <p className="mt-2 text-neutral-400">{recipe.description}</p>
        </div>

        {recipe.source === 'internal' && (
          <div className="flex gap-2 shrink-0">
            <Link
              to={`/recipes/${recipe.id}/edit`}
              className="flex items-center gap-1.5 rounded-lg border border-[#333] bg-[#1a1a1a] px-3 py-2 text-sm text-neutral-300 hover:border-neutral-600 hover:text-neutral-100 transition-all"
            >
              <Edit2 size={14} /> Edit
            </Link>
            <button
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              className="flex items-center gap-1.5 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400 hover:bg-red-500/20 transition-all disabled:opacity-50"
            >
              <Trash2 size={14} /> Delete
            </button>
          </div>
        )}
      </div>

      {/* Tags */}
      {recipe.tags.length > 0 && (
        <div className="mb-6 flex flex-wrap gap-1.5">
          {recipe.tags.map(tag => (
            <span
              key={tag}
              className="rounded-full bg-neutral-800 px-3 py-1 text-xs text-neutral-400"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="grid gap-8 sm:grid-cols-2">
        {/* Ingredients */}
        <div>
          <h2 className="flex items-center gap-2 text-lg font-semibold text-neutral-100 mb-4">
            <ChefHat size={18} className="text-amber-400" />
            Ingredients
            <span className="text-sm text-neutral-500 font-normal">({recipe.ingredients.length})</span>
          </h2>
          <ul className="space-y-2">
            {recipe.ingredients.map((ing, i) => (
              <li key={i} className="flex items-start gap-2.5">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400/60" />
                <span className="text-sm text-neutral-300">{ing}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Instructions */}
        <div>
          <h2 className="flex items-center gap-2 text-lg font-semibold text-neutral-100 mb-4">
            <CheckCircle2 size={18} className="text-amber-400" />
            Instructions
          </h2>
          <ol className="space-y-4">
            {recipe.instructions.map((step, i) => (
              <li key={i} className="flex gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-amber-500/10 text-xs font-semibold text-amber-400">
                  {i + 1}
                </span>
                <p className="text-sm text-neutral-300 leading-relaxed pt-0.5">{step}</p>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  )
}
