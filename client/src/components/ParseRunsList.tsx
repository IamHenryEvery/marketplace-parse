import { useParseRuns } from '@/hooks'
import { Badge } from '@/components/ui/badge'
import type { ParseRunListItem } from '@/types'

interface ParseRunsListProps {
  onRunClick: (run: ParseRunListItem) => void
}

const STATUS_LABELS: Record<ParseRunListItem['status'], string> = {
  pending: 'в очереди',
  running: 'идёт',
  completed: 'готово',
  failed: 'ошибка',
}

const STATUS_CLASS: Record<ParseRunListItem['status'], string> = {
  pending: 'text-muted-foreground',
  running: 'text-primary',
  completed: 'text-foreground',
  failed: 'text-destructive',
}

function formatTime(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function ParseRunsList({ onRunClick }: ParseRunsListProps) {
  const { data: runs = [], isLoading } = useParseRuns()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
      </div>
    )
  }

  if (runs.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        Запусков парсинга пока нет.
      </p>
    )
  }

  return (
    <div className="border border-border rounded-md overflow-hidden bg-card">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 text-left text-muted-foreground">
          <tr>
            <th className="px-4 py-2 font-medium">Когда</th>
            <th className="px-4 py-2 font-medium">Товар</th>
            <th className="px-4 py-2 font-medium">Маркетплейс</th>
            <th className="px-4 py-2 font-medium">Статус</th>
            <th className="px-4 py-2 font-medium text-right">Отзывов</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => {
            const when = run.started_at ?? run.created_at
            return (
              <tr
                key={run.run_id}
                onClick={() => onRunClick(run)}
                className="border-t border-border hover:bg-muted/30 cursor-pointer transition-colors"
                title={run.error_message ?? 'Кликните для просмотра диаграммы'}
              >
                <td className="px-4 py-2 text-muted-foreground whitespace-nowrap">
                  {formatTime(when)}
                </td>
                <td className="px-4 py-2 text-foreground">{run.product_name}</td>
                <td className="px-4 py-2">
                  <Badge variant="secondary">{run.marketplace.display_name}</Badge>
                </td>
                <td className={`px-4 py-2 ${STATUS_CLASS[run.status]}`}>
                  {STATUS_LABELS[run.status]}
                </td>
                <td className="px-4 py-2 text-foreground text-right">
                  {run.reviews_collected}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
