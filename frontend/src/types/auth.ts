export interface User {
  id: string
  email: string
  username: string
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface Favorite {
  id: string
  recipe_id: string
  recipe_source: string
  created_at: string
}
