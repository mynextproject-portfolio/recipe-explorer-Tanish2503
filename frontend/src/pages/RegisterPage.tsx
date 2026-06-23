import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Mail, Lock, User, ChefHat, Loader2 } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }
    setLoading(true)
    try {
      await register(email, username, password)
      navigate('/')
    } catch (err) {
      setError((err as Error).message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  const inputClass = 'w-full rounded-lg border border-[#333] bg-[#1a1a1a] px-4 py-2.5 pl-10 text-sm text-neutral-100 placeholder-neutral-600 outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 transition-all'

  return (
    <div className="mx-auto max-w-sm px-4 py-16 fade-in">
      <div className="mb-8 text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-amber-500/10">
          <ChefHat size={24} className="text-amber-400" />
        </div>
        <h1 className="text-2xl font-bold text-neutral-100">Create account</h1>
        <p className="mt-1 text-sm text-neutral-500">Start building your recipe collection</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        <div className="relative">
          <Mail size={16} className="absolute left-3 top-3.5 text-neutral-500" />
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="Email address"
            required
            className={inputClass}
          />
        </div>

        <div className="relative">
          <User size={16} className="absolute left-3 top-3.5 text-neutral-500" />
          <input
            type="text"
            value={username}
            onChange={e => setUsername(e.target.value)}
            placeholder="Username (letters, numbers, _ -)"
            required
            pattern="^[a-zA-Z0-9_-]+$"
            minLength={3}
            maxLength={50}
            className={inputClass}
          />
        </div>

        <div className="relative">
          <Lock size={16} className="absolute left-3 top-3.5 text-neutral-500" />
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="Password (min. 8 characters)"
            required
            minLength={8}
            className={inputClass}
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-xl bg-amber-500 py-2.5 text-sm font-semibold text-black hover:bg-amber-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
        >
          {loading && <Loader2 size={16} className="animate-spin" />}
          {loading ? 'Creating account…' : 'Create Account'}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-neutral-500">
        Already have an account?{' '}
        <Link to="/login" className="text-amber-400 hover:text-amber-300">
          Sign in
        </Link>
      </p>
    </div>
  )
}
