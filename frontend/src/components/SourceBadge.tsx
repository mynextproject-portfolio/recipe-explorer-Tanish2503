interface Props {
  source: 'internal' | 'external'
}

export function SourceBadge({ source }: Props) {
  if (source === 'external') {
    return (
      <span className="inline-flex items-center rounded-full bg-sky-500/10 px-2 py-0.5 text-xs font-medium text-sky-400 ring-1 ring-inset ring-sky-500/20">
        TheMealDB
      </span>
    )
  }
  return (
    <span className="inline-flex items-center rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-400 ring-1 ring-inset ring-emerald-500/20">
      My Collection
    </span>
  )
}
