import { useState, type FormEvent } from 'react'
import { useCreateProduct, useMarketplaces } from '@/hooks'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface CreateProductModalProps {
  open: boolean
  onClose: () => void
}

interface UrlRow {
  url: string
  marketplace_id: string
}

const emptyRow = (): UrlRow => ({ url: '', marketplace_id: '' })

export default function CreateProductModal({ open, onClose }: CreateProductModalProps) {
  const { data: marketplaces = [] } = useMarketplaces()
  const createMutation = useCreateProduct()
  const [name, setName] = useState('')
  const [urlRows, setUrlRows] = useState<UrlRow[]>([emptyRow(), emptyRow(), emptyRow()])
  const [error, setError] = useState('')

  const resetForm = () => {
    setName('')
    setUrlRows([emptyRow(), emptyRow(), emptyRow()])
    setError('')
  }

  const handleClose = () => {
    resetForm()
    onClose()
  }

  const updateRow = (index: number, field: keyof UrlRow, value: string) => {
    setUrlRows((prev) =>
      prev.map((row, i) => (i === index ? { ...row, [field]: value } : row))
    )
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    const validUrls = urlRows
      .filter((row) => row.url.trim() && row.marketplace_id)
      .map((row) => ({
        url: row.url.trim(),
        marketplace_id: parseInt(row.marketplace_id, 10),
      }))

    if (!name.trim()) {
      setError('Введите название товара')
      return
    }

    if (validUrls.length === 0) {
      setError('Добавьте хотя бы одну ссылку')
      return
    }

    try {
      await createMutation.mutateAsync({
        name: name.trim(),
        urls: validUrls,
      })
      handleClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка создания товара')
    }
  }

  return (
    <Modal open={open} onOpenChange={(isOpen) => !isOpen && handleClose()}>
      <ModalContent>
        <ModalHeader>
          <ModalTitle>Добавить товар</ModalTitle>
        </ModalHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="product-name">Название товара</Label>
            <Input
              id="product-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Например: Смартфон Samsung Galaxy"
              required
            />
          </div>

          <fieldset className="flex flex-col gap-3">
            <legend className="text-sm font-medium mb-2">Ссылки на маркетплейсы</legend>
            {urlRows.map((row, index) => (
              <div key={index} className="flex gap-2">
                <Input
                  value={row.url}
                  onChange={(e) => updateRow(index, 'url', e.target.value)}
                  placeholder="https://..."
                  className="flex-1"
                />
                <Select
                  value={row.marketplace_id}
                  onValueChange={(value) => updateRow(index, 'marketplace_id', value)}
                >
                  <SelectTrigger className="w-40">
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
            <Button type="button" variant="outline" onClick={handleClose}>
              Отмена
            </Button>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Создание...' : 'Создать'}
            </Button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  )
}
