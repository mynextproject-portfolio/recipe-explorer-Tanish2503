import { useState } from 'react'
import { Plus, X } from 'lucide-react'
import type { RecipeFormData } from '../types/recipe'

interface Props {
  initial?: RecipeFormData
  onSubmit: (data: RecipeFormData) => void
  isSubmitting: boolean
  submitLabel: string
  error?: string
}

const EMPTY: RecipeFormData = {
  title: '',
  description: '',
  cuisine: '',
  ingredients: [''],
  instructions: [''],
  tags: [],
}

export function RecipeForm({ initial, onSubmit, isSubmitting, submitLabel, error }: Props) {
  const [form, setForm] = useState<RecipeFormData>(initial ?? EMPTY)
  const [tagInput, setTagInput] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})

  const set = <K extends keyof RecipeFormData>(key: K, value: RecipeFormData[K]) =>
    setForm(f => ({ ...f, [key]: value }))

  const setListItem = (key: 'ingredients' | 'instructions', idx: number, val: string) =>
    setForm(f => {
      const arr = [...f[key]]
      arr[idx] = val
      return { ...f, [key]: arr }
    })

  const addListItem = (key: 'ingredients' | 'instructions') =>
    setForm(f => ({ ...f, [key]: [...f[key], ''] }))

  const removeListItem = (key: 'ingredients' | 'instructions', idx: number) =>
    setForm(f => ({ ...f, [key]: f[key].filter((_, i) => i !== idx) }))

  const addTag = () => {
    const tag = tagInput.trim()
    if (tag && !form.tags.includes(tag)) {
      setForm(f => ({ ...f, tags: [...f.tags, tag] }))
    }
    setTagInput('')
  }

  const removeTag = (tag: string) =>
    setForm(f => ({ ...f, tags: f.tags.filter(t => t !== tag) }))

  const validate = (): boolean => {
    const e: Record<string, string> = {}
    if (!form.title.trim()) e.title = 'Title is required'
    if (!form.description.trim()) e.description = 'Description is required'
    const ings = form.ingredients.filter(i => i.trim())
    if (!ings.length) e.ingredients = 'At least one ingredient is required'
    const steps = form.instructions.filter(i => i.trim())
    if (!steps.length) e.instructions = 'At least one step is required'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return
    onSubmit({
      ...form,
      ingredients: form.ingredients.filter(i => i.trim()),
      instructions: form.instructions.filter(i => i.trim()),
    })
  }

  const inputClass = (field?: string) =>
    `w-full rounded-lg border bg-[#1a1a1a] px-3 py-2 text-sm text-neutral-100 placeholder-neutral-600 outline-none transition-colors ${
      field && errors[field]
        ? 'border-red-500/50 focus:border-red-500'
        : 'border-[#333] focus:border-amber-500/50'
    }`

  const labelClass = 'block text-sm font-medium text-neutral-300 mb-1.5'

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Title */}
      <div>
        <label className={labelClass}>Title *</label>
        <input
          value={form.title}
          onChange={e => set('title', e.target.value)}
          placeholder="e.g. Spaghetti Carbonara"
          className={inputClass('title')}
        />
        {errors.title && <p className="mt-1 text-xs text-red-400">{errors.title}</p>}
      </div>

      {/* Description */}
      <div>
        <label className={labelClass}>Description *</label>
        <textarea
          value={form.description}
          onChange={e => set('description', e.target.value)}
          placeholder="Briefly describe the dish..."
          rows={3}
          className={inputClass('description') + ' resize-none'}
        />
        {errors.description && <p className="mt-1 text-xs text-red-400">{errors.description}</p>}
      </div>

      {/* Cuisine */}
      <div>
        <label className={labelClass}>Cuisine</label>
        <input
          value={form.cuisine}
          onChange={e => set('cuisine', e.target.value)}
          placeholder="e.g. Italian, Thai, Mexican"
          className={inputClass()}
        />
      </div>

      {/* Ingredients */}
      <div>
        <label className={labelClass}>Ingredients *</label>
        <div className="space-y-2">
          {form.ingredients.map((ing, i) => (
            <div key={i} className="flex gap-2">
              <input
                value={ing}
                onChange={e => setListItem('ingredients', i, e.target.value)}
                placeholder={`Ingredient ${i + 1}`}
                className={inputClass('ingredients')}
              />
              {form.ingredients.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeListItem('ingredients', i)}
                  className="text-neutral-600 hover:text-red-400 transition-colors"
                >
                  <X size={16} />
                </button>
              )}
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={() => addListItem('ingredients')}
          className="mt-2 flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 transition-colors"
        >
          <Plus size={14} /> Add ingredient
        </button>
        {errors.ingredients && <p className="mt-1 text-xs text-red-400">{errors.ingredients}</p>}
      </div>

      {/* Instructions */}
      <div>
        <label className={labelClass}>Instructions *</label>
        <div className="space-y-2">
          {form.instructions.map((step, i) => (
            <div key={i} className="flex gap-2">
              <span className="mt-2.5 min-w-[20px] text-xs text-neutral-500 font-mono">{i + 1}.</span>
              <textarea
                value={step}
                onChange={e => setListItem('instructions', i, e.target.value)}
                placeholder={`Step ${i + 1}...`}
                rows={2}
                className={inputClass('instructions') + ' resize-none'}
              />
              {form.instructions.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeListItem('instructions', i)}
                  className="mt-2 text-neutral-600 hover:text-red-400 transition-colors"
                >
                  <X size={16} />
                </button>
              )}
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={() => addListItem('instructions')}
          className="mt-2 flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 transition-colors"
        >
          <Plus size={14} /> Add step
        </button>
        {errors.instructions && <p className="mt-1 text-xs text-red-400">{errors.instructions}</p>}
      </div>

      {/* Tags */}
      <div>
        <label className={labelClass}>Tags</label>
        {form.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {form.tags.map(tag => (
              <span
                key={tag}
                className="flex items-center gap-1 rounded-full bg-neutral-800 px-2.5 py-1 text-xs text-neutral-300"
              >
                {tag}
                <button
                  type="button"
                  onClick={() => removeTag(tag)}
                  className="text-neutral-500 hover:text-red-400"
                >
                  <X size={10} />
                </button>
              </span>
            ))}
          </div>
        )}
        <div className="flex gap-2">
          <input
            value={tagInput}
            onChange={e => setTagInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addTag() } }}
            placeholder="Add a tag..."
            className={inputClass()}
          />
          <button
            type="button"
            onClick={addTag}
            className="rounded-lg bg-neutral-800 px-3 text-sm text-neutral-300 hover:bg-neutral-700 transition-colors"
          >
            Add
          </button>
        </div>
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full rounded-xl bg-amber-500 py-3 text-sm font-semibold text-black hover:bg-amber-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isSubmitting ? 'Saving...' : submitLabel}
      </button>
    </form>
  )
}
