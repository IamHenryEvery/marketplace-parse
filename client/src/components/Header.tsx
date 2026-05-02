import { useNavigate } from 'react-router-dom'
import { useMe, useLogout, useToggleScheduler } from '@/hooks'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { LogOut } from 'lucide-react'

export default function Header() {
  const navigate = useNavigate()
  const { data: user } = useMe()
  const logoutMutation = useLogout()
  const toggleSchedulerMutation = useToggleScheduler()

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
