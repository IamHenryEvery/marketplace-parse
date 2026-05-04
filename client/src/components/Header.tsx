import { useNavigate, useLocation, Link } from 'react-router-dom'
import { useMe, useLogout, useToggleScheduler } from '@/hooks'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { BarChart3, LogOut, Shield } from 'lucide-react'

export default function Header() {
  const navigate = useNavigate()
  const location = useLocation()
  const { data: user } = useMe()
  const logoutMutation = useLogout()
  const toggleSchedulerMutation = useToggleScheduler()
  const isAdminRoute = location.pathname.startsWith('/admin')
  const isAnalyticsRoute = location.pathname.startsWith('/analytics')
  const canSeeAnalytics = user?.role === 'analyst' || user?.role === 'admin'

  const handleLogout = async () => {
    await logoutMutation.mutateAsync()
    navigate('/login')
  }

  const handleToggleScheduler = async () => {
    await toggleSchedulerMutation.mutateAsync()
  }

  return (
    <header className="border-b border-border bg-card">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        <h1 className="text-lg font-semibold text-foreground">marketplace-parse</h1>

        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <Switch
              id="scheduler"
              checked={user?.scheduler_enabled ?? false}
              onCheckedChange={handleToggleScheduler}
              disabled={toggleSchedulerMutation.isPending}
            />
            <Label htmlFor="scheduler" className="text-sm text-muted-foreground cursor-pointer">
              Авто-парсинг раз в сутки
            </Label>
          </div>

          <span className="text-sm text-muted-foreground">{user?.email}</span>

          {canSeeAnalytics && (
            <Link
              to={isAnalyticsRoute ? '/' : '/analytics'}
              className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <BarChart3 className="h-4 w-4" />
              {isAnalyticsRoute ? 'К товарам' : 'Аналитика'}
            </Link>
          )}

          {user?.role === 'admin' && (
            <Link
              to={isAdminRoute ? '/' : '/admin'}
              className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <Shield className="h-4 w-4" />
              {isAdminRoute ? 'К товарам' : 'Админка'}
            </Link>
          )}

          <button
            onClick={handleLogout}
            disabled={logoutMutation.isPending}
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <LogOut className="h-4 w-4" />
            Выйти
          </button>
        </div>
      </div>
    </header>
  )
}
