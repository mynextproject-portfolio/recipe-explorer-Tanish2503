import { Link } from 'react-router-dom'
import { Clock, ChefHat } from 'lucide-react'
import type { Recipe } from '../types/recipe'
import { SourceBadge } from './SourceBadge'
import { FavoriteButton } from './FavoriteButton'

const FALLBACK_IMAGES = [
  'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400&h=250&fit=crop',
  'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=400&h=250&fit=crop',
  'https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=400&h=250&fit=crop',
  'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=400&h=250&fit=crop',
  'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=400&h=250&fit=crop',
  'https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=400&h=250&fit=crop',
]

function getFallbackImage(id: string): string {
  let hash = 0
  for (let i = 0; i < id.length; i++) hash = (hash * 31 + id.charCodeAt(i)) >>> 0
  return FALLBACK_IMAGES[hash % FALLBACK_IMAGES.length]
}

interface Props {
  recipe: Recipe
}

export function RecipeCard({ recipe }: Props) {
  const detailPath =
    recipe.source === 'external'
      ? `/recipes/external/${recipe.id}`
      : `/recipes/${recipe.id}`

  const img = recipe.image || getFallbackImage(recipe.id)

  return (
    <Link
      to={detailPath}
      className="group flex flex-col rounded-xl bg-[#141414] border border-[#262626] overflow-hidden hover:border-neutral-600 hover:shadow-lg hover:shadow-black/50 transition-all duration-200"
    >
      {/* Image */}
      <div className="relative h-44 overflow-hidden bg-[#1a1a1a]">
        <img
          src={img}
          alt={recipe.title}
          className="h-full w-full object-cover transition-transform duration-400 group-hover:scale-105"
          loading="lazy"
          onError={e => {
            const t = e.currentTarget
            t.src = FALLBACK_IMAGES[0]
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
        <div className="absolute bottom-2 left-2">
          <SourceBadge source={recipe.source} />
        </div>
        <div className="absolute top-2 right-2">
          <FavoriteButton recipeId={recipe.id} source={recipe.source} />
        </div>
      </div>

      {/* Body */}
      <div className="flex flex-col flex-1 p-4 gap-2">
        <h3 className="font-semibold text-neutral-100 leading-snug line-clamp-2 group-hover:text-amber-300 transition-colors">
          {recipe.title}
        </h3>

        {recipe.cuisine && (
          <span className="text-xs text-amber-400/80 font-medium uppercase tracking-wide">
            {recipe.cuisine}
          </span>
        )}

        <p className="text-sm text-neutral-400 line-clamp-2 flex-1">
          {recipe.description}
        </p>

        {recipe.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            {recipe.tags.slice(0, 3).map(tag => (
              <span
                key={tag}
                className="rounded-full bg-neutral-800 px-2 py-0.5 text-xs text-neutral-400"
              >
                {tag}
              </span>
            ))}
            {recipe.tags.length > 3 && (
              <span className="rounded-full bg-neutral-800 px-2 py-0.5 text-xs text-neutral-500">
                +{recipe.tags.length - 3}
              </span>
            )}
          </div>
        )}

        <div className="flex items-center gap-3 pt-1 text-xs text-neutral-500">
          <span className="flex items-center gap-1">
            <ChefHat size={12} />
            {recipe.ingredients.length} ingredients
          </span>
          <span className="flex items-center gap-1">
            <Clock size={12} />
            {recipe.instructions.length} steps
          </span>
        </div>
      </div>
    </Link>
  )
}
