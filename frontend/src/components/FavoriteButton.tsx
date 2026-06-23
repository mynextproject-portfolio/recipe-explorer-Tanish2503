import { Heart } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useToggleFavorite } from '../hooks/useFavorites'

interface Props {
  recipeId: string
  source: string
  className?: string
}

export function FavoriteButton({ recipeId, source, className = '' }: Props) {
  const navigate = useNavigate()
  const { isFavorite, toggle, isLoading, isAuthenticated } = useToggleFavorite(recipeId, source)

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!isAuthenticated) {
      navigate('/login')
      return
    }
    toggle()
  }

  return (
    <button
      onClick={handleClick}
      disabled={isLoading}
      title={isAuthenticated ? (isFavorite ? 'Remove from favorites' : 'Add to favorites') : 'Sign in to save favorites'}
      className={`flex h-7 w-7 items-center justify-center rounded-full transition-all ${
        isFavorite
          ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
          : 'bg-black/40 text-white/60 hover:bg-black/60 hover:text-white'
      } ${isLoading ? 'opacity-50 cursor-wait' : ''} ${className}`}
    >
      <Heart size={14} fill={isFavorite ? 'currentColor' : 'none'} />
    </button>
  )
}
