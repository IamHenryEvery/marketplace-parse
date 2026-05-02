import type {
  User,
  UserRole,
  AdminUser,
  Marketplace,
  Product,
  CreateProductPayload,
  UpdateProductPayload,
  ProgressResponse,
  AnalysisItem,
} from './types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${endpoint}`

  const config: RequestInit = {
    ...options,
    credentials: 'include',
    headers: {
      ...options.headers,
    },
  }

  if (options.body && options.method !== 'GET') {
    config.headers = {
      ...config.headers,
      'Content-Type': 'application/json',
    }
  }

  const response = await fetch(url, config)

  if (response.status === 204) {
    return undefined as T
  }

  if (response.status === 401) {
    window.location.href = '/login'
    throw new ApiError(401, 'Unauthorized')
  }

  const data = await response.json()

  if (!response.ok) {
    throw new ApiError(response.status, data.detail || response.statusText)
  }

  return data as T
}

// Auth
export async function register(email: string, password: string): Promise<User> {
  return request<User>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export async function login(email: string, password: string): Promise<User> {
  return request<User>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export async function logout(): Promise<void> {
  return request<void>('/api/auth/logout', { method: 'POST' })
}

export async function getMe(): Promise<User> {
  return request<User>('/api/me')
}

// Marketplaces
export async function getMarketplaces(): Promise<Marketplace[]> {
  return request<Marketplace[]>('/api/marketplaces')
}

// Products
export async function getProducts(): Promise<Product[]> {
  return request<Product[]>('/api/products')
}

export async function getProduct(id: number): Promise<Product> {
  return request<Product>(`/api/products/${id}`)
}

export async function createProduct(
  payload: CreateProductPayload
): Promise<Product> {
  return request<Product>('/api/products', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function updateProduct(
  id: number,
  payload: UpdateProductPayload
): Promise<Product> {
  return request<Product>(`/api/products/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export async function deleteProduct(id: number): Promise<void> {
  return request<void>(`/api/products/${id}`, { method: 'DELETE' })
}

// Parsing
export async function startParsing(
  productId: number
): Promise<{ run_ids: number[] }> {
  return request<{ run_ids: number[] }>(`/api/products/${productId}/parse`, {
    method: 'POST',
  })
}

export async function getParseStatus(
  productId: number
): Promise<ProgressResponse> {
  return request<ProgressResponse>(`/api/products/${productId}/parse/status`)
}

// Analysis
export async function getAnalysis(productId: number): Promise<AnalysisItem[]> {
  return request<AnalysisItem[]>(`/api/products/${productId}/analysis`)
}

// Scheduler
export async function toggleScheduler(): Promise<{ scheduler_enabled: boolean }> {
  return request<{ scheduler_enabled: boolean }>('/api/scheduler/toggle', {
    method: 'POST',
  })
}

// Admin
export async function getAdminUsers(): Promise<AdminUser[]> {
  return request<AdminUser[]>('/api/admin/users')
}

export async function updateUserRole(
  userId: number,
  role: UserRole
): Promise<AdminUser> {
  return request<AdminUser>(`/api/admin/users/${userId}/role`, {
    method: 'PATCH',
    body: JSON.stringify({ role }),
  })
}

export async function deleteUser(userId: number): Promise<void> {
  return request<void>(`/api/admin/users/${userId}`, { method: 'DELETE' })
}
