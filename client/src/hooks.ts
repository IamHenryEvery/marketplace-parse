import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from './api'
import type {
  CreateProductPayload,
  FeedFilters,
  UpdateProductPayload,
  UserRole,
} from './types'

// Auth hooks
export function useMe() {
  return useQuery({
    queryKey: ['me'],
    queryFn: api.getMe,
    staleTime: 30_000,
    retry: false,
  })
}

export function useLogin() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      api.login(email, password),
    onSuccess: (data) => {
      queryClient.setQueryData(['me'], data)
    },
  })
}

export function useRegister() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      api.register(email, password),
    onSuccess: (data) => {
      queryClient.setQueryData(['me'], data)
    },
  })
}

export function useLogout() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.logout,
    onSuccess: () => {
      queryClient.clear()
    },
  })
}

// Marketplaces
export function useMarketplaces() {
  return useQuery({
    queryKey: ['marketplaces'],
    queryFn: api.getMarketplaces,
    staleTime: 30_000,
  })
}

// Products
export function useProducts() {
  return useQuery({
    queryKey: ['products'],
    queryFn: api.getProducts,
  })
}

export function useProduct(id: number) {
  return useQuery({
    queryKey: ['products', id],
    queryFn: () => api.getProduct(id),
    enabled: !!id,
  })
}

export function useCreateProduct() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: CreateProductPayload) => api.createProduct(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })
}

export function useUpdateProduct() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: number
      payload: UpdateProductPayload
    }) => api.updateProduct(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })
}

export function useDeleteProduct() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.deleteProduct(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })
}

// Parsing
export function useStartParsing() {
  return useMutation({
    mutationFn: (productId: number) => api.startParsing(productId),
  })
}

export function useParseStatus(productId: number, enabled: boolean = true) {
  return useQuery({
    queryKey: ['parse-status', productId],
    queryFn: () => api.getParseStatus(productId),
    staleTime: 0,
    refetchInterval: enabled ? 2000 : false,
    enabled,
  })
}

// Analysis
export function useAnalysis(productId: number, enabled: boolean = true) {
  return useQuery({
    queryKey: ['analysis', productId],
    queryFn: () => api.getAnalysis(productId),
    enabled,
  })
}

// Parse run history
export function useParseRuns() {
  return useQuery({
    queryKey: ['parse-runs'],
    queryFn: api.getParseRuns,
    refetchInterval: 5000,
    staleTime: 0,
  })
}

export function useRunAnalysis(runId: number | null) {
  return useQuery({
    queryKey: ['run-analysis', runId],
    queryFn: () => api.getRunAnalysis(runId!),
    enabled: runId !== null,
  })
}

// Analytics (analyst+admin)
export function useAnalyticsFeed(filters: FeedFilters) {
  return useQuery({
    queryKey: ['analytics-feed', filters],
    queryFn: () => api.getAnalyticsFeed(filters),
    staleTime: 10_000,
  })
}

// Admin
export function useAdminUsers() {
  return useQuery({
    queryKey: ['admin-users'],
    queryFn: api.getAdminUsers,
    staleTime: 0,
  })
}

export function useUpdateUserRole() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, role }: { userId: number; role: UserRole }) =>
      api.updateUserRole(userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    },
  })
}

export function useDeleteUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (userId: number) => api.deleteUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    },
  })
}

// Scheduler
export function useToggleScheduler() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.toggleScheduler,
    onSuccess: (data) => {
      queryClient.setQueryData(['me'], (old: unknown) => {
        if (old && typeof old === 'object' && 'scheduler_enabled' in old) {
          return { ...old, scheduler_enabled: data.scheduler_enabled }
        }
        return old
      })
    },
  })
}
