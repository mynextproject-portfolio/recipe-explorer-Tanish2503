import { Search, X, Loader2 } from 'lucide-react'

interface Props {
  value: string
  onChange: (v: string) => void
  isSearching: boolean
  resultCount?: number
}

export function SearchBar({ value, onChange, isSearching, resultCount }: Props) {
  return (
    <div className="relative w-full">
      <div className="relative flex items-center">
        <div className="absolute left-3 text-neutral-500">
          {isSearching ? (
            <Loader2 size={18} className="animate-spin text-amber-400" />
          ) : (
            <Search size={18} />
          )}
        </div>
        <input
          type="text"
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder="Search recipes by name, cuisine, or ingredient..."
          className="w-full rounded-xl border border-[#262626] bg-[#141414] py-3 pl-10 pr-10 text-sm text-neutral-100 placeholder-neutral-500 outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 transition-all"
        />
        {value && (
          <button
            onClick={() => onChange('')}
            className="absolute right-3 text-neutral-500 hover:text-neutral-300 transition-colors"
            aria-label="Clear search"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {value && !isSearching && resultCount !== undefined && (
        <p className="mt-2 text-xs text-neutral-500">
          Found <span className="text-neutral-300 font-medium">{resultCount}</span> recipe{resultCount !== 1 ? 's' : ''} for &ldquo;{value}&rdquo;
        </p>
      )}
    </div>
  )
}
