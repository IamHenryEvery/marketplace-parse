import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useRegister } from '@/hooks'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export default function RegisterPage() {
  const navigate = useNavigate()
  const registerMutation = useRegister()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    try {
      await registerMutation.mutateAsync({ email, password })
      navigate('/')
    } catch {
      
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-foreground">Анализ отзывов</h1>
          <p className="text-muted-foreground mt-2">Создайте аккаунт</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="email@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="password">Пароль</Label>
            <Input
              id="password"
              type="password"
              placeholder="Минимум 6 символов"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              autoComplete="new-password"
            />
          </div>

          {registerMutation.isError && (
            <p className="text-sm text-destructive">
              {registerMutation.error instanceof Error
                ? registerMutation.error.message
                : 'Ошибка регистрации'}
            </p>
          )}

          <Button type="submit" disabled={registerMutation.isPending} className="mt-2">
            {registerMutation.isPending ? 'Регистрация...' : 'Зарегистрироваться'}
          </Button>
        </form>

        <p className="text-center text-sm text-muted-foreground mt-6">
          Уже есть аккаунт?{' '}
          <Link to="/login" className="text-primary hover:underline">
            Войти
          </Link>
        </p>
      </div>
    </div>
  )
}
