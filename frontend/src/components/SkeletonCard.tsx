export function SkeletonCard() {
  return (
    <div className="flex flex-col rounded-xl bg-[#141414] border border-[#262626] overflow-hidden">
      <div className="skeleton h-44 w-full" />
      <div className="p-4 flex flex-col gap-3">
        <div className="skeleton h-5 w-3/4" />
        <div className="skeleton h-3 w-1/3" />
        <div className="skeleton h-4 w-full" />
        <div className="skeleton h-4 w-5/6" />
        <div className="flex gap-2 mt-1">
          <div className="skeleton h-5 w-12 rounded-full" />
          <div className="skeleton h-5 w-16 rounded-full" />
        </div>
        <div className="flex gap-4">
          <div className="skeleton h-3 w-20" />
          <div className="skeleton h-3 w-16" />
        </div>
      </div>
    </div>
  )
}
