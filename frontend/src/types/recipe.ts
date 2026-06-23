export interface Recipe {
  id: string
  title: string
  description: string
  cuisine: string
  ingredients: string[]
  instructions: string[]
  tags: string[]
  source: 'internal' | 'external'
  image?: string
  created_at?: string
  updated_at?: string
}

export interface RecipeSearchResponse {
  recipes: Recipe[]
  timing?: {
    internal_ms: number
    external_ms?: number
  }
  external_search_error?: string
}

export interface RecipeFormData {
  title: string
  description: string
  cuisine: string
  ingredients: string[]
  instructions: string[]
  tags: string[]
}
