import { useEffect, useRef, useState } from 'react'
import { Navigate } from 'react-router-dom'
import {
  useAdminUsers,
  useDeleteUser,
  useMe,
  useUpdateUserRole,
} from '@/hooks'
import Header from '@/components/Header'
import type { AdminUser, UserRole } from '@/types'

type Menu = {
  x: number
  y: number
  user: AdminUser
}

const ROLE_LABELS: Record<UserRole, string> = {
  user: 'Пользователь',
  analyst: 'Аналитик',
  admin: 'Админ',
}

const ROLES: UserRole[] = ['user', 'analyst', 'admin']

export default function AdminPanelPage() {
  const { data: me, isLoading: meLoading } = useMe()
  const { data: users = [], isLoading } = useAdminUsers()
  const updateRole = useUpdateUserRole()
  const deleteUser = useDeleteUser()
  const [menu, setMenu] = useState<Menu | null>(null)
  const menuRef = useRef<HTMLDivElement | null>(null)

  // Close menu on outside click / Esc / scroll
  useEffect(() => {
    if (!menu) return
    const onDown = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenu(null)
      }
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenu(null)
    }
    const onScroll = () => setMenu(null)
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    window.addEventListener('scroll', onScroll, true)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
      window.removeEventListener('scroll', onScroll, true)
    }
  }, [menu])

  if (meLoading) return null
  if (!me || me.role !== 'admin') return <Navigate to="/" replace />

  const handleContextMenu = (e: React.MouseEvent, user: AdminUser) => {
    e.preventDefault()
    setMenu({ x: e.clientX, y: e.clientY, user })
  }

  const handleChangeRole = async (role: UserRole) => {
    if (!menu) return
    if (menu.user.role === role) {
      setMenu(null)
      return
    }
    try {
      await updateRole.mutateAsync({ userId: menu.user.user_id, role })
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Ошибка смены роли')
    } finally {
      setMenu(null)
    }
  }

  const handleDelete = async () => {
    if (!menu) return
    if (
      !confirm(
        `Удалить пользователя ${menu.user.email}? Все его товары и собранные отзывы исчезнут.`
      )
    ) {
      setMenu(null)
      return
    }
    try {
      await deleteUser.mutateAsync(menu.user.user_id)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Ошибка удаления')
    } finally {
      setMenu(null)
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1 max-w-6xl mx-auto w-full px-4 py-8">
        <h2 className="text-xl font-semibold text-foreground mb-2">
          Админ-панель
        </h2>
        <p className="text-sm text-muted-foreground mb-6">
          Кликните правой кнопкой по строке пользователя, чтобы изменить роль или удалить.
        </p>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          </div>
        ) : (
          <div className="border border-border rounded-md overflow-hidden bg-card">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-left text-muted-foreground">
                <tr>
                  <th className="px-4 py-2 font-medium">ID</th>
                  <th className="px-4 py-2 font-medium">Email</th>
                  <th className="px-4 py-2 font-medium">Роль</th>
                  <th className="px-4 py-2 font-medium">Активен</th>
                  <th className="px-4 py-2 font-medium">Создан</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr
                    key={u.user_id}
                    onContextMenu={(e) => handleContextMenu(e, u)}
                    className={`border-t border-border hover:bg-muted/30 cursor-context-menu ${
                      u.user_id === me.user_id ? 'opacity-60' : ''
                    }`}
                    title={
                      u.user_id === me.user_id
                        ? 'Это вы — действия над собой запрещены'
                        : 'ПКМ для действий'
                    }
                  >
                    <td className="px-4 py-2 text-muted-foreground">{u.user_id}</td>
                    <td className="px-4 py-2 text-foreground">{u.email}</td>
                    <td className="px-4 py-2 text-foreground">
                      {ROLE_LABELS[u.role]}
                    </td>
                    <td className="px-4 py-2 text-muted-foreground">
                      {u.is_active ? 'да' : 'нет'}
                    </td>
                    <td className="px-4 py-2 text-muted-foreground">
                      {new Date(u.created_at).toLocaleString('ru-RU')}
                    </td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-4 py-6 text-center text-muted-foreground"
                    >
                      Пользователей нет.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </main>

      {menu && menu.user.user_id !== me.user_id && (
        <div
          ref={menuRef}
          style={{ left: menu.x, top: menu.y }}
          className="fixed z-50 min-w-[200px] rounded-md border border-border bg-popover text-popover-foreground shadow-md py-1"
        >
          <div className="px-3 py-1.5 text-xs text-muted-foreground border-b border-border">
            {menu.user.email}
          </div>
          {ROLES.map((role) => {
            const isCurrent = menu.user.role === role
            return (
              <button
                key={role}
                disabled={isCurrent || updateRole.isPending}
                onClick={() => handleChangeRole(role)}
                className="w-full text-left px-3 py-1.5 text-sm hover:bg-muted disabled:opacity-50 disabled:hover:bg-transparent disabled:cursor-default"
              >
                {isCurrent ? '✓ ' : ''}Сделать: {ROLE_LABELS[role]}
              </button>
            )
          })}
          <div className="border-t border-border my-1" />
          <button
            disabled={deleteUser.isPending}
            onClick={handleDelete}
            className="w-full text-left px-3 py-1.5 text-sm text-destructive hover:bg-destructive/10 disabled:opacity-50"
          >
            Удалить пользователя
          </button>
        </div>
      )}
    </div>
  )
}
