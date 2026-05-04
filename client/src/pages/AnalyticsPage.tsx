import { useMemo, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { Download } from 'lucide-react'

import { useMe, useMarketplaces, useAnalyticsFeed } from '@/hooks'
import { analyticsExportUrl } from '@/api'
import Header from '@/components/Header'
import { Badge } from '@/components/ui/badge'
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
import type { FeedFilters, SentimentLabel } from '@/types'

const SENTIMENT_LABELS: Record<SentimentLabel, string> = {
  positive: 'позитив',
  neutral: 'нейтрал',
  negative: 'негатив',
}

const SENTIMENT_CLASS: Record<SentimentLabel, string> = {
  positive: 'text-positive',
  neutral: 'text-muted-foreground',
  negative: 'text-destructive',
}

const PAGE_SIZE = 50

export default function AnalyticsPage() {
  const { data: me, isLoading: meLoading } = useMe()
  const { data: marketplaces = [] } = useMarketplaces()

  // Filter state — empty string means "all". Local-only until "Применить".
  const [marketplace, setMarketplace] = useState<string>('')
  const [sentiment, setSentiment] = useState<string>('')
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')
  const [page, setPage] = useState(0)

  const filters: FeedFilters = useMemo(
    () => ({
      marketplace: marketplace || undefined,
      sentiment: (sentiment as SentimentLabel) || undefined,
      from: dateFrom || undefined,
      to: dateTo || undefined,
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    }),
    [marketplace, sentiment, dateFrom, dateTo, page]
  )

  const { data: items = [], isLoading } = useAnalyticsFeed(filters)

  const resetPageThen = (fn: () => void) => {
    setPage(0)
    fn()
  }

  if (meLoading) return null
  if (!me || (me.role !== 'analyst' && me.role !== 'admin')) {
    return <Navigate to="/" replace />
  }

  const exportHref = analyticsExportUrl({
    marketplace: filters.marketplace,
    sentiment: filters.sentiment,
    from: filters.from,
    to: filters.to,
  })

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1 max-w-6xl mx-auto w-full px-4 py-8">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xl font-semibold text-foreground">Аналитика</h2>
          <a href={exportHref}>
            <Button variant="outline">
              <Download className="h-4 w-4 mr-2" />
              Скачать CSV
            </Button>
          </a>
        </div>
        <p className="text-sm text-muted-foreground mb-6">
          Все собранные отзывы по всем пользователям. Имена аккаунтов скрыты.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 mb-4 p-4 border border-border rounded-md bg-card">
          <div>
            <Label className="text-xs text-muted-foreground">Маркетплейс</Label>
            <Select
              value={marketplace || 'all'}
              onValueChange={(v) => resetPageThen(() => setMarketplace(v === 'all' ? '' : v))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Все" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все маркетплейсы</SelectItem>
                {marketplaces.map((m) => (
                  <SelectItem key={m.marketplace_id} value={m.slug}>
                    {m.display_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label className="text-xs text-muted-foreground">Тональность</Label>
            <Select
              value={sentiment || 'all'}
              onValueChange={(v) => resetPageThen(() => setSentiment(v === 'all' ? '' : v))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Все" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все</SelectItem>
                <SelectItem value="positive">Позитив</SelectItem>
                <SelectItem value="neutral">Нейтрал</SelectItem>
                <SelectItem value="negative">Негатив</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label className="text-xs text-muted-foreground">С даты</Label>
            <Input
              type="date"
              value={dateFrom}
              onChange={(e) => resetPageThen(() => setDateFrom(e.target.value))}
            />
          </div>

          <div>
            <Label className="text-xs text-muted-foreground">По дату</Label>
            <Input
              type="date"
              value={dateTo}
              onChange={(e) => resetPageThen(() => setDateTo(e.target.value))}
            />
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          </div>
        ) : items.length === 0 ? (
          <p className="text-sm text-muted-foreground py-8 text-center">
            По выбранным фильтрам отзывов нет.
          </p>
        ) : (
          <>
            <div className="border border-border rounded-md overflow-hidden bg-card">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 text-left text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2 font-medium whitespace-nowrap">Когда</th>
                    <th className="px-4 py-2 font-medium">Товар</th>
                    <th className="px-4 py-2 font-medium">Маркетплейс</th>
                    <th className="px-4 py-2 font-medium">Тон</th>
                    <th className="px-4 py-2 font-medium">Текст</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((it) => (
                    <tr key={it.review_id} className="border-t border-border align-top">
                      <td className="px-4 py-2 text-muted-foreground whitespace-nowrap">
                        {new Date(it.created_at).toLocaleDateString('ru-RU')}
                      </td>
                      <td className="px-4 py-2 text-foreground">{it.product_name}</td>
                      <td className="px-4 py-2">
                        <Badge variant="secondary">{it.marketplace.display_name}</Badge>
                      </td>
                      <td
                        className={`px-4 py-2 ${
                          it.sentiment_label
                            ? SENTIMENT_CLASS[it.sentiment_label]
                            : 'text-muted-foreground'
                        }`}
                      >
                        {it.sentiment_label
                          ? SENTIMENT_LABELS[it.sentiment_label]
                          : '—'}
                      </td>
                      <td className="px-4 py-2 text-foreground max-w-xl">
                        <span className="line-clamp-3">{it.review_text}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between mt-4">
              <span className="text-xs text-muted-foreground">
                Страница {page + 1}
                {items.length < PAGE_SIZE ? ' (последняя)' : ''}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  disabled={page === 0}
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                >
                  ← Назад
                </Button>
                <Button
                  variant="outline"
                  disabled={items.length < PAGE_SIZE}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Вперёд →
                </Button>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  )
}
