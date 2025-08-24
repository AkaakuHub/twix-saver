import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

interface AppState {
  isLoading: boolean
  error: string | null
  notifications: Notification[]
  sidebarCollapsed: boolean

  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  addNotification: (notification: Omit<Notification, 'id'>) => void
  removeNotification: (id: string) => void
  clearNotifications: () => void
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
}

interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message?: string
  duration?: number
}

export const useAppStore = create<AppState>()(
  devtools(
    (set, get) => ({
      isLoading: false,
      error: null,
      notifications: [],
      sidebarCollapsed: false,

      setLoading: loading => set({ isLoading: loading }),

      setError: error => set({ error }),

      addNotification: notification => {
        const id = Date.now().toString()
        const newNotification = { ...notification, id }

        set(state => ({
          notifications: [...state.notifications, newNotification],
        }))

        if (notification.duration !== 0) {
          setTimeout(() => {
            get().removeNotification(id)
          }, notification.duration || 5000)
        }
      },

      removeNotification: id =>
        set(state => ({
          notifications: state.notifications.filter(n => n.id !== id),
        })),

      clearNotifications: () => set({ notifications: [] }),

      toggleSidebar: () => set(state => ({ sidebarCollapsed: !state.sidebarCollapsed })),

      setSidebarCollapsed: collapsed => set({ sidebarCollapsed: collapsed }),
    }),
    {
      name: 'app-store',
    }
  )
)
