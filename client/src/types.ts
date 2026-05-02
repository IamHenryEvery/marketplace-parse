// Auth & User
export type UserRole = 'user' | 'analyst' | 'admin'

export interface User {
  user_id: number
  email: string
  role: UserRole
  scheduler_enabled: boolean
}

// Admin view of a user — has extra fields the dashboard doesn't need
export interface AdminUser {
  user_id: number
  email: string
  role: UserRole
  is_active: boolean
  scheduler_enabled: boolean
  created_at: string
}

// Marketplaces
export interface Marketplace {
  marketplace_id: number
  slug: string
  display_name: string
}

// Products
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

// Parsing
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

// Analysis
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
