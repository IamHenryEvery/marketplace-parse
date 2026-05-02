import { useAnalysis } from '@/hooks'
import type { Product, AnalysisItem } from '@/types'
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalTitle,
} from '@/components/ui/modal'
import { Button } from '@/components/ui/button'
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'

interface AnalysisModalProps {
  open: boolean
  product: Product
  onClose: () => void
}

const COLORS = {
  positive: '#16a34a',
  neutral: '#94a3b8',
  negative: '#dc2626',
}

function SentimentChart({ item }: { item: AnalysisItem }) {
  if (!item.latest || item.latest.total_reviews === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 bg-secondary/30 rounded-lg">
        <p className="text-sm text-muted-foreground">Данных пока нет</p>
      </div>
    )
  }

  const data = [
    { name: 'Позитив', value: item.latest.positive_count, color: COLORS.positive },
    { name: 'Нейтрал', value: item.latest.neutral_count, color: COLORS.neutral },
    { name: 'Негатив', value: item.latest.negative_count, color: COLORS.negative },
  ].filter((d) => d.value > 0)

  return (
    <div className="flex flex-col items-center">
      <ResponsiveContainer width="100%" height={180}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={40}
            outerRadius={70}
            paddingAngle={2}
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number) => [`${value} отзывов`, '']}
            contentStyle={{
              backgroundColor: 'var(--background)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
            }}
          />
          <Legend
            verticalAlign="bottom"
            height={36}
            formatter={(value) => <span className="text-xs">{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
      <p className="text-xs text-muted-foreground mt-2">
        всего: {item.latest.total_reviews} · средняя: {item.latest.avg_sentiment.toFixed(2)}
      </p>
    </div>
  )
}

export default function AnalysisModal({ open, product, onClose }: AnalysisModalProps) {
  const { data: analysis = [], isLoading } = useAnalysis(product.product_id, open)

  return (
    <Modal open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <ModalContent className="max-w-2xl">
        <ModalHeader>
          <ModalTitle>{product.name} — тональность</ModalTitle>
        </ModalHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          </div>
        ) : analysis.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            Нет данных для анализа
          </p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {analysis.map((item) => (
              <div
                key={item.marketplace.marketplace_id}
                className="p-4 border border-border rounded-lg"
              >
                <h4 className="text-sm font-medium text-center mb-2">
                  {item.marketplace.display_name}
                </h4>
                <SentimentChart item={item} />
              </div>
            ))}
          </div>
        )}

        <Button variant="outline" onClick={onClose} className="self-end mt-4">
          Закрыть
        </Button>
      </ModalContent>
    </Modal>
  )
}
