import { Plus } from 'lucide-react'

interface AddProductCardProps {
  onClick: () => void
}

export default function AddProductCard({ onClick }: AddProductCardProps) {
  return (
    <button
      onClick={onClick}
      className="border-2 border-dashed border-border rounded-lg p-4 flex flex-col items-center justify-center gap-2 hover:border-primary/50 hover:bg-accent/50 transition-all cursor-pointer min-h-[100px]"
    >
      <Plus className="h-6 w-6 text-muted-foreground" />
      <span className="text-sm text-muted-foreground">Добавить товар</span>
    </button>
  )
}
