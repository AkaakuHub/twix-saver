import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { TargetUser } from '../types/api'

interface UserState {
  users: TargetUser[]
  selectedUsers: Set<string>
  filters: UserFilters
  pagination: {
    page: number
    pageSize: number
    total: number
  }

  setUsers: (users: TargetUser[]) => void
  addUser: (user: TargetUser) => void
  updateUser: (id: string, updates: Partial<TargetUser>) => void
  deleteUser: (id: string) => void
  toggleUserSelection: (id: string) => void
  selectAllUsers: () => void
  clearSelection: () => void
  setFilters: (filters: Partial<UserFilters>) => void
  setPagination: (pagination: Partial<UserState['pagination']>) => void
}

interface UserFilters {
  search: string
  status: 'all' | 'active' | 'inactive' | 'error'
  priority: 'all' | 'high' | 'medium' | 'low'
  sortBy: 'username' | 'last_scraped' | 'priority' | 'created_at'
  sortOrder: 'asc' | 'desc'
}

export const useUserStore = create<UserState>()(
  devtools(
    set => ({
      users: [],
      selectedUsers: new Set(),
      filters: {
        search: '',
        status: 'all',
        priority: 'all',
        sortBy: 'created_at',
        sortOrder: 'desc',
      },
      pagination: {
        page: 1,
        pageSize: 20,
        total: 0,
      },

      setUsers: users => set({ users }),

      addUser: user => set(state => ({ users: [...state.users, user] })),

      updateUser: (id, updates) =>
        set(state => ({
          users: state.users.map(user => (user.username === id ? { ...user, ...updates } : user)),
        })),

      deleteUser: id =>
        set(state => ({
          users: state.users.filter(user => user.username !== id),
          selectedUsers: new Set([...state.selectedUsers].filter(userId => userId !== id)),
        })),

      toggleUserSelection: id =>
        set(state => {
          const newSelection = new Set(state.selectedUsers)
          if (newSelection.has(id)) {
            newSelection.delete(id)
          } else {
            newSelection.add(id)
          }
          return { selectedUsers: newSelection }
        }),

      selectAllUsers: () =>
        set(state => ({
          selectedUsers: new Set(state.users.map(user => user.username)),
        })),

      clearSelection: () => set({ selectedUsers: new Set() }),

      setFilters: newFilters => set(state => ({ filters: { ...state.filters, ...newFilters } })),

      setPagination: newPagination =>
        set(state => ({
          pagination: { ...state.pagination, ...newPagination },
        })),
    }),
    {
      name: 'user-store',
    }
  )
)
