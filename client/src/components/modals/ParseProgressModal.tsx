import { useEffect } from 'react'
import { useParseStatus } from '@/hooks'
import { formatDateTime } from '@/lib/utils'
import type { Product, ParseRunSummary } from '@/types'
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalTitle,
} from '@/components/ui/modal'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'

interface ParseProgressModalProps {
  open: boolean
  product: Product
  onClose: () => void
  onComplete: () => void
}

function getStatusBadge(status: ParseRunSummary['last_run']) {
  if (!status) return <Badge variant="secondary">Не запускался</Badge>

  switch (status.status) {
    case 'pending':
      return <Badge variant="pending">В очереди</Badge>
    case 'running':
      return <Badge variant="warning">Выполняется</Badge>
    case 'completed':
      return <Badge variant="success">Завершён</Badge>
    case 'failed':
      return <Badge variant="destructive">Ошибка</Badge>
    default:
      return <Badge variant="secondary">Неизвестно</Badge>
  }
}

export default function ParseProgressModal({
  open,
  product,
  onClose,
  onComplete,
}: ParseProgressModalProps) {
  const { data: progress } = useParseStatus(product.product_id, open)

  const total = progress?.total ?? 0
  const done = (progress?.completed ?? 0) + (progress?.failed ?? 0)
  const inFlight = progress?.in_flight ?? 0
  const pending = progress?.pending ?? 0
  const running = progress?.running ?? 0
  const failed = progress?.failed ?? 0

  const progressValue = total > 0 ? (done / total) * 100 : 0

  // Auto-switch to analysis when done
  useEffect(() => {
    if (open && inFlight === 0 && total > 0) {
      onComplete()
    }
  }, [open, inFlight, total, onComplete])

  return (
    <Modal open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <ModalContent className="max-w-xl">
        <ModalHeader>
          <ModalTitle>{product.name} — парсинг</ModalTitle>
        </ModalHeader>

        <div className="flex flex-col gap-4">
          <p className="text-sm text-muted-foreground">
            {done} из {total} готово · в работе: {running} · в очереди: {pending} · упало: {failed}
          </p>

          <Progress value={progressValue} className="h-3" />

          <div className="flex flex-col gap-2 max-h-60 overflow-y-auto">
            {progress?.runs.map((run) => (
              <div
                key={run.url_id}
                className="flex flex-col gap-1 p-3 bg-secondary/50 rounded-lg"
              >
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="shrink-0">
                    {run.marketplace.display_name}
                  </Badge>
                  {getStatusBadge(run.last_run)}
                </div>
                <code className="text-xs text-muted-foreground break-all">{run.url}</code>
                {run.last_run?.status === 'completed' && (
                  <p className="text-xs text-muted-foreground">
                    Собрано отзывов: {run.last_run.reviews_collected}
                    {run.last_run.finished_at && ` · ${formatDateTime(run.last_run.finished_at)}`}
                  </p>
                )}
                {run.last_run?.status === 'failed' && run.last_run.error_message && (
                  <p className="text-xs text-destructive">{run.last_run.error_message}</p>
                )}
              </div>
            ))}
          </div>

          <Button variant="outline" onClick={onClose} className="self-end">
            Закрыть
          </Button>
        </div>
      </ModalContent>
    </Modal>
  )
}
