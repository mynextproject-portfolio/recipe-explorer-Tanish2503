import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { useRecipe, useUpdateRecipe } from '../hooks/useRecipes'
import { RecipeForm } from '../components/RecipeForm'

export function EditRecipePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: recipe, isLoading } = useRecipe(id!, 'internal')
  const mutation = useUpdateRecipe(id!)

  if (isLoading) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-10 space-y-4">
        <div className="skeleton h-5 w-24" />
        <div className="skeleton h-8 w-48" />
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="skeleton h-10 w-full" />
        ))}
      </div>
    )
  }

  if (!recipe) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-20 text-center">
        <p className="text-neutral-400">Recipe not found.</p>
        <Link to="/" className="text-sm text-amber-400 mt-3 inline-block hover:text-amber-300">
          ← Back
        </Link>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <Link
        to={`/recipes/${id}`}
        className="mb-6 flex items-center gap-1.5 text-sm text-neutral-400 hover:text-neutral-200 transition-colors w-fit"
      >
        <ArrowLeft size={16} /> Back to recipe
      </Link>

      <h1 className="text-2xl font-bold text-neutral-100 mb-1">Edit Recipe</h1>
      <p className="text-sm text-neutral-500 mb-8 truncate">{recipe.title}</p>

      <RecipeForm
        initial={{
          title: recipe.title,
          description: recipe.description,
          cuisine: recipe.cuisine,
          ingredients: recipe.ingredients,
          instructions: recipe.instructions,
          tags: recipe.tags,
        }}
        onSubmit={data =>
          mutation.mutateAsync(data).then(() => navigate(`/recipes/${id}`))
        }
        isSubmitting={mutation.isPending}
        submitLabel="Save Changes"
        error={mutation.error ? (mutation.error as Error).message : undefined}
      />
    </div>
  )
}
