import { useNavigate, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { useCreateRecipe } from '../hooks/useRecipes'
import { RecipeForm } from '../components/RecipeForm'

export function AddRecipePage() {
  const navigate = useNavigate()
  const mutation = useCreateRecipe()

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <Link
        to="/"
        className="mb-6 flex items-center gap-1.5 text-sm text-neutral-400 hover:text-neutral-200 transition-colors w-fit"
      >
        <ArrowLeft size={16} /> All recipes
      </Link>

      <h1 className="text-2xl font-bold text-neutral-100 mb-1">New Recipe</h1>
      <p className="text-sm text-neutral-500 mb-8">Add a new recipe to your collection</p>

      <RecipeForm
        onSubmit={data =>
          mutation.mutateAsync(data).then(r => navigate(`/recipes/${r.id}`))
        }
        isSubmitting={mutation.isPending}
        submitLabel="Create Recipe"
        error={mutation.error ? (mutation.error as Error).message : undefined}
      />
    </div>
  )
}
