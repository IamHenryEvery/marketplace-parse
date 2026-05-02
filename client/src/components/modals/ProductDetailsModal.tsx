import { useDeleteProduct, useStartParsing } from '@/hooks'
import { pluralize, formatDate } from '@/lib/utils'
import type { Product } from '@/types'
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalTitle,
} from '@/components/ui/modal'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Pencil, Trash2, Play } from 'lucide-react'

interface ProductDetailsModalProps {
  open: boolean
  product: Product
  onClose: () => void
  onEdit: () => void
  onStartParsing: () => void
}

export default function ProductDetailsModal({
  open,
  product,
  onClose,
  onEdit,
  onStartParsing,
}: ProductDetailsModalProps) {
  const deleteMutation = useDeleteProduct()
  const parseMutation = useStartParsing()

  const handleDelete = async () => {
    if (!window.confirm(`Удалить товар "${product.name}"?`)) return
    try {
      await deleteMutation.mutateAsync(product.product_id)
      onClose()
    } catch {
      // Error handled silently
    }
  }

  const handleStartParsing = async () => {
    try {
      await parseMutation.mutateAsync(product.product_id)
      onStartParsing()
    } catch {
      // Error handled silently
    }
  }

  const urlCount = product.urls.length
  const linkWord = pluralize(urlCount, 'ссылка', 'ссылки', 'ссылок')

  return (
    <Modal open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <ModalContent className="max-w-xl">
        <ModalHeader>
          <ModalTitle>{product.name}</ModalTitle>
          <p className="text-sm text-muted-foreground">
            Создан {formatDate(product.created_at)}
          </p>
        </ModalHeader>

        <div className="flex gap-2 mb-4">
          <Button variant="outline" size="sm" onClick={onEdit}>
            <Pencil className="h-4 w-4 mr-1.5" />
            Редактировать
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDelete}
            disabled={deleteMutation.isPending}
            className="text-destructive hover:text-destructive"
          >
            <Trash2 className="h-4 w-4 mr-1.5" />
            Удалить
          </Button>
        </div>

        <div className="flex flex-col gap-3 mb-6">
          <h4 className="text-sm font-medium">Ссылки</h4>
          {product.urls.length === 0 ? (
            <p className="text-sm text-muted-foreground">Нет ссылок</p>
          ) : (
            product.urls.map((u) => (
              <div
                key={u.url_id}
                className="flex items-start gap-2 p-2 bg-secondary/50 rounded-lg"
              >
                <Badge variant="secondary" className="shrink-0">
                  {u.marketplace.display_name}
                </Badge>
                <code className="text-xs break-all text-muted-foreground flex-1">
                  {u.url}
                </code>
              </div>
            ))
          )}
        </div>

        {urlCount > 0 ? (
          <Button
            onClick={handleStartParsing}
            disabled={parseMutation.isPending}
            className="w-full"
          >
            <Play className="h-4 w-4 mr-2" />
            {parseMutation.isPending
              ? 'Запуск...'
              : `Запустить парсинг (${urlCount} ${linkWord})`}
          </Button>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-2">
            {"Добавьте ссылки через 'Редактировать'"}
          </p>
        )}
      </ModalContent>
    </Modal>
  )
}
