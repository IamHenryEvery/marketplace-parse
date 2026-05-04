import { useRunAnalysis } from '@/hooks'
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalTitle,
} from '@/components/ui/modal'
import { Button } from '@/components/ui/button'
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'

interface RunAnalysisModalProps {
  open: boolean
  runId: number | null
  onClose: () => void
}

const COLORS = {
  positive: '#16a34a',
  neutral: '#94a3b8',
  negative: '#dc2626',
}

export default function RunAnalysisModal({
  open,
  runId,
  onClose,
}: RunAnalysisModalProps) {
  const { data, isLoading } = useRunAnalysis(open ? runId : null)

  const close = () => onClose()

  return (
    <Modal open={open} onOpenChange={(isOpen) => !isOpen && close()}>
      <ModalContent className="max-w-md">
        <ModalHeader>
          <ModalTitle>
            {data ? `${data.product_name} — ${data.marketplace.display_name}` : 'Тональность прогона'}
          </ModalTitle>
        </ModalHeader>

        {isLoading || !data ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          </div>
        ) : data.total_reviews === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            {data.status === 'completed'
              ? 'В этом прогоне отзывов не собрано.'
              : data.status === 'failed'
                ? 'Прогон завершился ошибкой — данных нет.'
                : 'Прогон ещё не завершён.'}
          </p>
        ) : (
          <div className="flex flex-col items-center">
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={[
                    { name: 'Позитив', value: data.positive_count, color: COLORS.positive },
                    { name: 'Нейтрал', value: data.neutral_count, color: COLORS.neutral },
                    { name: 'Негатив', value: data.negative_count, color: COLORS.negative },
                  ].filter((d) => d.value > 0)}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={90}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {[COLORS.positive, COLORS.neutral, COLORS.negative].map((c, i) => (
                    <Cell key={i} fill={c} />
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
            <p className="text-sm text-muted-foreground mt-2">
              всего: <span className="text-foreground font-medium">{data.total_reviews}</span> ·
              средняя: {data.avg_sentiment.toFixed(2)}
            </p>
          </div>
        )}

        <Button variant="outline" onClick={close} className="self-end mt-4">
          Закрыть
        </Button>
      </ModalContent>
    </Modal>
  )
}
