// Auth & User
export type UserRole = 'user' | 'analyst' | 'admin'

export interface User {
  user_id: number
  email: string
  role: UserRole
  scheduler_enabled: boolean
}

export interface AdminUser {
  user_id: number
  email: string
  role: UserRole
  scheduler_enabled: boolean
  created_at: string
}


export interface Marketplace {
  marketplace_id: number
  slug: string
  display_name: string
}


export interface ProductURL {
  url_id: number
  url: string
  marketplace: Marketplace
}

export interface Product {
  product_id: number
  name: string
  created_at: string
  urls: ProductURL[]
}

export interface CreateProductPayload {
  name: string
  urls: { url: string; marketplace_id: number }[]
}

export interface UpdateProductPayload {
  name?: string
  urls_update?: { url_id: number; url?: string; marketplace_id?: number }[]
  urls_delete?: number[]
  urls_add?: { url: string; marketplace_id: number }[]
}


export interface ParseRunSummary {
  url_id: number
  url: string
  marketplace: { display_name: string }
  last_run: {
    status: 'pending' | 'running' | 'completed' | 'failed'
    started_at: string | null
    finished_at: string | null
    reviews_collected: number
    error_message: string | null
  } | null
}

export interface ProgressResponse {
  pending: number
  running: number
  completed: number
  failed: number
  in_flight: number
  total: number
  runs: ParseRunSummary[]
}


export interface AnalysisItem {
  marketplace: Marketplace
  latest: {
    total_reviews: number
    positive_count: number
    negative_count: number
    neutral_count: number
    avg_sentiment: number
    calculated_at: string
  } | null
}


export interface ParseRunListItem {
  run_id: number
  product_id: number
  product_name: string
  url: string
  marketplace: Marketplace
  status: 'pending' | 'running' | 'completed' | 'failed'
  started_at: string | null
  finished_at: string | null
  created_at: string
  reviews_collected: number
  error_message: string | null
}

export interface RunAnalysis {
  run_id: number
  product_name: string
  marketplace: Marketplace
  status: 'pending' | 'running' | 'completed' | 'failed'
  total_reviews: number
  positive_count: number
  negative_count: number
  neutral_count: number
  avg_sentiment: number
}


export type SentimentLabel = 'positive' | 'neutral' | 'negative'

export interface FeedReviewItem {
  review_id: number
  review_text: string
  review_date: string | null
  sentiment_label: SentimentLabel | null
  sentiment_score: number | null
  created_at: string
  marketplace: Marketplace
  product_name: string
}

export interface FeedFilters {
  marketplace?: string
  sentiment?: SentimentLabel
  from?: string  
  to?: string    
  limit?: number
  offset?: number
}
