import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Menu, X, ChefHat, Plus, LogOut, Heart } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

export function Navbar() {
  const [open, setOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  const handleLogout = () => {
    logout()
    setUserMenuOpen(false)
    navigate('/')
  }

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
            {user && (
              <Link
                to="/favorites"
                className={`flex items-center gap-1.5 text-sm font-medium transition-colors ${
                  pathname === '/favorites' ? 'text-amber-400' : 'text-neutral-400 hover:text-neutral-100'
                }`}
              >
                <Heart size={14} />
                Favorites
              </Link>
            )}
            {navLink('/recipes/new', 'Add Recipe')}

            {user ? (
              <div className="relative">
                <button
                  onClick={() => setUserMenuOpen(o => !o)}
                  className="flex items-center gap-2 rounded-lg bg-neutral-800 px-3 py-1.5 text-sm text-neutral-200 hover:bg-neutral-700 transition-colors"
                >
                  <div className="flex h-5 w-5 items-center justify-center rounded-full bg-amber-500/20 text-amber-400 text-xs font-bold">
                    {user.username[0].toUpperCase()}
                  </div>
                  {user.username}
                </button>
                {userMenuOpen && (
                  <div className="absolute right-0 mt-2 w-44 rounded-xl border border-[#262626] bg-[#141414] shadow-lg shadow-black/50 overflow-hidden">
                    <div className="border-b border-[#262626] px-3 py-2">
                      <p className="text-xs text-neutral-500 truncate">{user.email}</p>
                    </div>
                    <button
                      onClick={handleLogout}
                      className="flex w-full items-center gap-2 px-3 py-2.5 text-sm text-neutral-300 hover:bg-neutral-800 hover:text-red-400 transition-colors"
                    >
                      <LogOut size={14} /> Sign out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  to="/login"
                  className="text-sm font-medium text-neutral-400 hover:text-neutral-100 transition-colors"
                >
                  Sign in
                </Link>
                <Link
                  to="/register"
                  className="flex items-center gap-1.5 rounded-lg bg-amber-500 px-3 py-1.5 text-sm font-medium text-black hover:bg-amber-400 transition-colors"
                >
                  <Plus size={14} />
                  Join free
                </Link>
              </div>
            )}
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
            {user && navLink('/favorites', 'Favorites')}
            {navLink('/recipes/new', 'Add Recipe')}
            {user ? (
              <button
                onClick={() => { handleLogout(); setOpen(false) }}
                className="flex items-center gap-2 text-sm text-red-400"
              >
                <LogOut size={14} /> Sign out ({user.username})
              </button>
            ) : (
              <>
                {navLink('/login', 'Sign in')}
                {navLink('/register', 'Create account')}
              </>
            )}
          </div>
        )}
      </div>
    </nav>
  )
}
