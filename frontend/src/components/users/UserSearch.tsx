import { useUserStore } from '../../stores/userStore'
import { useDebounce } from '../../hooks/useDebounce'
import { Input } from '../ui/Input'
import { Button } from '../ui/Button'
import { MagnifyingGlassIcon, FunnelIcon } from '@heroicons/react/24/outline'
import { useState, useEffect } from 'react'

export const UserSearch = () => {
  const { filters, setFilters } = useUserStore()
  const [searchInput, setSearchInput] = useState(filters.search)
  const [showAdvanced, setShowAdvanced] = useState(false)

  const debouncedSearch = useDebounce(searchInput, 300)

  useEffect(() => {
    setFilters({ search: debouncedSearch })
  }, [debouncedSearch, setFilters])

  const handleReset = () => {
    setSearchInput('')
    setFilters({
      search: '',
      status: 'all',
      priority: 'all',
      sortBy: 'created_at',
      sortOrder: 'desc',
    })
    setShowAdvanced(false)
  }

  return (
    <div className="bg-white p-4 rounded-lg border border-gray-200 space-y-4">
      <div className="flex items-center space-x-4">
        <div className="flex-1">
          <Input
            placeholder="ユーザー名で検索..."
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
            leftIcon={<MagnifyingGlassIcon className="w-4 h-4" />}
          />
        </div>

        <Button
          variant="outline"
          onClick={() => setShowAdvanced(!showAdvanced)}
          icon={<FunnelIcon className="w-4 h-4" />}
        >
          詳細フィルタ
        </Button>

        <Button variant="ghost" onClick={handleReset}>
          リセット
        </Button>
      </div>

      {showAdvanced && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-4 border-t border-gray-200">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">ステータス</label>
            <select
              value={filters.status}
              onChange={e =>
                setFilters({ status: e.target.value as 'all' | 'active' | 'inactive' | 'error' })
              }
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            >
              <option value="all">すべて</option>
              <option value="active">有効</option>
              <option value="inactive">無効</option>
              <option value="error">エラー</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">優先度</label>
            <select
              value={filters.priority}
              onChange={e =>
                setFilters({ priority: e.target.value as 'all' | 'high' | 'medium' | 'low' })
              }
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            >
              <option value="all">すべて</option>
              <option value="high">高</option>
              <option value="medium">中</option>
              <option value="low">低</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">並び順</label>
            <select
              value={filters.sortBy}
              onChange={e =>
                setFilters({
                  sortBy: e.target.value as 'username' | 'last_scraped' | 'priority' | 'created_at',
                })
              }
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            >
              <option value="username">ユーザー名</option>
              <option value="created_at">作成日</option>
              <option value="last_scraped">最終実行日</option>
              <option value="priority">優先度</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">順序</label>
            <select
              value={filters.sortOrder}
              onChange={e => setFilters({ sortOrder: e.target.value as 'asc' | 'desc' })}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            >
              <option value="desc">降順</option>
              <option value="asc">昇順</option>
            </select>
          </div>
        </div>
      )}
    </div>
  )
}
