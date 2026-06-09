import { useState, useEffect, type FormEvent } from 'react'
import { useUpdateProduct, useMarketplaces } from '@/hooks'
import type { Product, UpdateProductPayload } from '@/types'
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalTitle,
  ModalFooter,
} from '@/components/ui/modal'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface EditProductModalProps {
  open: boolean
  product: Product
  onClose: () => void
}

interface ExistingUrlRow {
  url_id: number
  url: string
  marketplace_id: string
  originalUrl: string
  originalMarketplaceId: string
  toDelete: boolean
}

interface NewUrlRow {
  url: string
  marketplace_id: string
}

const emptyNewRow = (): NewUrlRow => ({ url: '', marketplace_id: '' })

export default function EditProductModal({ open, product, onClose }: EditProductModalProps) {
  const { data: marketplaces = [] } = useMarketplaces()
  const updateMutation = useUpdateProduct()
  const [name, setName] = useState('')
  const [existingUrls, setExistingUrls] = useState<ExistingUrlRow[]>([])
  const [newUrls, setNewUrls] = useState<NewUrlRow[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    if (open && product) {
      setName(product.name)
      setExistingUrls(
        product.urls.map((u) => ({
          url_id: u.url_id,
          url: u.url,
          marketplace_id: String(u.marketplace.marketplace_id),
          originalUrl: u.url,
          originalMarketplaceId: String(u.marketplace.marketplace_id),
          toDelete: false,
        }))
      )
      setNewUrls([emptyNewRow(), emptyNewRow(), emptyNewRow()])
      setError('')
    }
  }, [open, product])

  const updateExistingRow = (
    index: number,
    field: keyof ExistingUrlRow,
    value: string | boolean
  ) => {
    setExistingUrls((prev) =>
      prev.map((row, i) => (i === index ? { ...row, [field]: value } : row))
    )
  }

  const updateNewRow = (index: number, field: keyof NewUrlRow, value: string) => {
    setNewUrls((prev) =>
      prev.map((row, i) => (i === index ? { ...row, [field]: value } : row))
    )
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    const payload: UpdateProductPayload = {
      name: name.trim(),
    }

    const urlsUpdate = existingUrls
      .filter(
        (row) =>
          !row.toDelete &&
          (row.url !== row.originalUrl || row.marketplace_id !== row.originalMarketplaceId)
      )
      .map((row) => ({
        url_id: row.url_id,
        ...(row.url !== row.originalUrl && { url: row.url }),
        ...(row.marketplace_id !== row.originalMarketplaceId && {
          marketplace_id: parseInt(row.marketplace_id, 10),
        }),
      }))

    if (urlsUpdate.length > 0) {
      payload.urls_update = urlsUpdate
    }

    const urlsDelete = existingUrls.filter((row) => row.toDelete).map((row) => row.url_id)
    if (urlsDelete.length > 0) {
      payload.urls_delete = urlsDelete
    }

    const urlsAdd = newUrls
      .filter((row) => row.url.trim() && row.marketplace_id)
      .map((row) => ({
        url: row.url.trim(),
        marketplace_id: parseInt(row.marketplace_id, 10),
      }))
    if (urlsAdd.length > 0) {
      payload.urls_add = urlsAdd
    }

    try {
      await updateMutation.mutateAsync({ id: product.product_id, payload })
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка обновления товара')
    }
  }

  return (
    <Modal open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <ModalContent className="max-w-xl">
        <ModalHeader>
          <ModalTitle>Редактировать товар</ModalTitle>
        </ModalHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="edit-product-name">Название товара</Label>
            <Input
              id="edit-product-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          {existingUrls.length > 0 && (
            <fieldset className="flex flex-col gap-3">
              <legend className="text-sm font-medium mb-2">Существующие ссылки</legend>
              {existingUrls.map((row, index) => (
                <div
                  key={row.url_id}
                  className={`flex gap-2 items-center ${row.toDelete ? 'opacity-50' : ''}`}
                >
                  <Input
                    value={row.url}
                    onChange={(e) => updateExistingRow(index, 'url', e.target.value)}
                    disabled={row.toDelete}
                    className="flex-1"
                  />
                  <Select
                    value={row.marketplace_id}
                    onValueChange={(value) => updateExistingRow(index, 'marketplace_id', value)}
                    disabled={row.toDelete}
                  >
                    <SelectTrigger className="w-36">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {marketplaces.map((mp) => (
                        <SelectItem key={mp.marketplace_id} value={String(mp.marketplace_id)}>
                          {mp.display_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <label className="flex items-center gap-1.5 text-xs text-muted-foreground whitespace-nowrap">
                    <Checkbox
                      checked={row.toDelete}
                      onCheckedChange={(checked) =>
                        updateExistingRow(index, 'toDelete', checked === true)
                      }
                    />
                    Удалить
                  </label>
                </div>
              ))}
            </fieldset>
          )}

          <fieldset className="flex flex-col gap-3">
            <legend className="text-sm font-medium mb-2">Новые ссылки</legend>
            {newUrls.map((row, index) => (
              <div key={index} className="flex gap-2">
                <Input
                  value={row.url}
                  onChange={(e) => updateNewRow(index, 'url', e.target.value)}
                  placeholder="https://..."
                  className="flex-1"
                />
                <Select
                  value={row.marketplace_id}
                  onValueChange={(value) => updateNewRow(index, 'marketplace_id', value)}
                >
                  <SelectTrigger className="w-36">
                    <SelectValue placeholder="Маркетплейс" />
                  </SelectTrigger>
                  <SelectContent>
                    {marketplaces.map((mp) => (
                      <SelectItem key={mp.marketplace_id} value={String(mp.marketplace_id)}>
                        {mp.display_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            ))}
          </fieldset>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <ModalFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Отмена
            </Button>
            <Button type="submit" disabled={updateMutation.isPending}>
              {updateMutation.isPending ? 'Сохранение...' : 'Сохранить'}
            </Button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  )
}
