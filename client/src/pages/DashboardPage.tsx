import { useState } from 'react'
import { useProducts } from '@/hooks'
import Header from '@/components/Header'
import ProductCard from '@/components/ProductCard'
import AddProductCard from '@/components/AddProductCard'
import ParseRunsList from '@/components/ParseRunsList'
import CreateProductModal from '@/components/modals/CreateProductModal'
import ProductDetailsModal from '@/components/modals/ProductDetailsModal'
import EditProductModal from '@/components/modals/EditProductModal'
import ParseProgressModal from '@/components/modals/ParseProgressModal'
import AnalysisModal from '@/components/modals/AnalysisModal'
import RunAnalysisModal from '@/components/modals/RunAnalysisModal'
import type { Product, ParseRunListItem } from '@/types'

type ModalType =
  | 'create'
  | 'details'
  | 'edit'
  | 'progress'
  | 'analysis'
  | 'run-analysis'
  | null

export default function DashboardPage() {
  const { data: products = [], isLoading } = useProducts()
  const [modalType, setModalType] = useState<ModalType>(null)
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null)
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null)

  const openDetails = (product: Product) => {
    setSelectedProduct(product)
    setModalType('details')
  }

  const openCreate = () => {
    setModalType('create')
  }

  const openEdit = () => {
    setModalType('edit')
  }

  const openProgress = () => {
    setModalType('progress')
  }

  const openAnalysis = () => {
    setModalType('analysis')
  }

  const closeModal = () => {
    setModalType(null)
  }

  const closeAndClearProduct = () => {
    setModalType(null)
    setSelectedProduct(null)
  }

  const openRunAnalysis = (run: ParseRunListItem) => {
    setSelectedRunId(run.run_id)
    setModalType('run-analysis')
  }

  const closeRunAnalysis = () => {
    setModalType(null)
    setSelectedRunId(null)
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1 max-w-6xl mx-auto w-full px-4 py-8">
        <h2 className="text-xl font-semibold text-foreground mb-6">Товары</h2>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          </div>
        ) : products.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground mb-4">
              У вас пока нет товаров. Добавьте первый товар, чтобы начать отслеживать отзывы.
            </p>
            <button
              onClick={openCreate}
              className="inline-flex items-center gap-2 text-primary hover:underline"
            >
              Добавить товар
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {products.map((product) => (
              <ProductCard
                key={product.product_id}
                product={product}
                onClick={() => openDetails(product)}
              />
            ))}
            <AddProductCard onClick={openCreate} />
          </div>
        )}

        <h2 className="text-xl font-semibold text-foreground mt-12 mb-2">
          История прогонов
        </h2>
        <p className="text-sm text-muted-foreground mb-4">
          Кликните по строке, чтобы увидеть круговую диаграмму отзывов этого прогона.
        </p>
        <ParseRunsList onRunClick={openRunAnalysis} />
      </main>

      <CreateProductModal
        open={modalType === 'create'}
        onClose={closeModal}
      />

      {selectedProduct && (
        <>
          <ProductDetailsModal
            open={modalType === 'details'}
            product={selectedProduct}
            onClose={closeAndClearProduct}
            onEdit={openEdit}
            onStartParsing={openProgress}
          />

          <EditProductModal
            open={modalType === 'edit'}
            product={selectedProduct}
            onClose={() => setModalType('details')}
          />

          <ParseProgressModal
            open={modalType === 'progress'}
            product={selectedProduct}
            onClose={closeAndClearProduct}
            onComplete={openAnalysis}
          />

          <AnalysisModal
            open={modalType === 'analysis'}
            product={selectedProduct}
            onClose={closeAndClearProduct}
          />
        </>
      )}

      <RunAnalysisModal
        open={modalType === 'run-analysis'}
        runId={selectedRunId}
        onClose={closeRunAnalysis}
      />
    </div>
  )
}
