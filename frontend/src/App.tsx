import { Routes, Route } from 'react-router-dom'
import { Navbar } from './components/Navbar'
import { HomePage } from './pages/HomePage'
import { RecipeDetailPage } from './pages/RecipeDetailPage'
import { AddRecipePage } from './pages/AddRecipePage'
import { EditRecipePage } from './pages/EditRecipePage'

function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-center">
      <span className="text-6xl">🍽️</span>
      <h2 className="text-2xl font-bold text-neutral-200">Page not found</h2>
      <p className="text-neutral-500">The page you're looking for doesn't exist.</p>
      <a href="/" className="mt-2 text-sm text-amber-400 hover:text-amber-300">
        ← Back to recipes
      </a>
    </div>
  )
}

export default function App() {
  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      <Navbar />
      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/recipes/new" element={<AddRecipePage />} />
          <Route path="/recipes/external/:id" element={<RecipeDetailPage />} />
          <Route path="/recipes/:id/edit" element={<EditRecipePage />} />
          <Route path="/recipes/:id" element={<RecipeDetailPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <footer className="border-t border-[#1a1a1a] mt-16 py-6">
        <p className="text-center text-xs text-neutral-700">
          Recipe Explorer · Built with FastAPI + React + TheMealDB
        </p>
      </footer>
    </div>
  )
}
