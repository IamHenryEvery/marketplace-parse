import type { Product } from '@/types'
import { Badge } from '@/components/ui/badge'

interface ProductCardProps {
  product: Product
  onClick: () => void
}

export default function ProductCard({ product, onClick }: ProductCardProps) {
  // Get unique marketplaces
  const uniqueMarketplaces = Array.from(
    new Map(product.urls.map((u) => [u.marketplace.marketplace_id, u.marketplace])).values()
  )

  return (
    <button
      onClick={onClick}
      className="bg-card border border-border rounded-lg p-4 text-left hover:border-primary/50 hover:shadow-sm transition-all cursor-pointer"
    >
      <h3 className="font-medium text-foreground mb-3 line-clamp-2">{product.name}</h3>
      <div className="flex flex-wrap gap-1.5">
        {uniqueMarketplaces.map((mp) => (
          <Badge key={mp.marketplace_id} variant="secondary">
            {mp.display_name}
          </Badge>
        ))}
        {uniqueMarketplaces.length === 0 && (
          <span className="text-xs text-muted-foreground">Нет ссылок</span>
        )}
      </div>
    </button>
  )
}
