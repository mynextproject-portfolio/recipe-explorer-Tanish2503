import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Menu, X, ChefHat, Plus } from 'lucide-react'

export function Navbar() {
  const [open, setOpen] = useState(false)
  const { pathname } = useLocation()

  const navLink = (to: string, label: string) => (
    <Link
      to={to}
      onClick={() => setOpen(false)}
      className={`text-sm font-medium transition-colors duration-150 ${
        pathname === to
          ? 'text-amber-400'
          : 'text-neutral-400 hover:text-neutral-100'
      }`}
    >
      {label}
    </Link>
  )

  return (
    <nav className="sticky top-0 z-50 border-b border-neutral-800 bg-[#0a0a0a]/95 backdrop-blur-sm">
      <div className="mx-auto max-w-6xl px-4">
        <div className="flex h-14 items-center justify-between">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/10 text-amber-400 group-hover:bg-amber-500/20 transition-colors">
              <ChefHat size={18} />
            </div>
            <span className="font-semibold text-neutral-100 tracking-tight">
              Recipe<span className="text-amber-400">Explorer</span>
            </span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-6">
            {navLink('/', 'Browse')}
            {navLink('/recipes/new', 'Add Recipe')}
            <Link
              to="/recipes/new"
              className="flex items-center gap-1.5 rounded-lg bg-amber-500 px-3 py-1.5 text-sm font-medium text-black hover:bg-amber-400 transition-colors"
            >
              <Plus size={14} />
              New
            </Link>
          </div>

          {/* Mobile toggle */}
          <button
            className="md:hidden text-neutral-400 hover:text-neutral-100"
            onClick={() => setOpen(o => !o)}
            aria-label="Toggle menu"
          >
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {/* Mobile menu */}
        {open && (
          <div className="md:hidden border-t border-neutral-800 py-3 flex flex-col gap-3">
            {navLink('/', 'Browse')}
            {navLink('/recipes/new', 'Add Recipe')}
          </div>
        )}
      </div>
    </nav>
  )
}
