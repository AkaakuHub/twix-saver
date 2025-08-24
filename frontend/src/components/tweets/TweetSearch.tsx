import { useState } from 'react'
import { MagnifyingGlassIcon, FunnelIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { Card } from '../ui/Card'
import { useDebounceCallback } from '../../hooks/useDebounceCallback'

interface TweetSearchProps {
  onSearch: (query: string) => void
  onFiltersChange: (filters: TweetFilters) => void
  className?: string
}

export interface TweetFilters {
  query: string
  dateFrom?: string
  dateTo?: string
  username?: string
  hasMedia?: boolean
  hasArticles?: boolean
  minEngagement?: number
  hashtags?: string[]
  sortBy: 'date' | 'engagement' | 'relevance'
  sortOrder: 'desc' | 'asc'
}

const initialFilters: TweetFilters = {
  query: '',
  sortBy: 'date',
  sortOrder: 'desc',
}

export const TweetSearch = ({ onSearch, onFiltersChange, className = '' }: TweetSearchProps) => {
  const [filters, setFilters] = useState<TweetFilters>(initialFilters)
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false)
  const [hashtagInput, setHashtagInput] = useState('')

  // デバウンスされた検索実行
  const debouncedSearch = useDebounceCallback((searchFilters: TweetFilters) => {
    onSearch(searchFilters.query)
    onFiltersChange(searchFilters)
  }, 300)

  const updateFilters = (newFilters: Partial<TweetFilters>) => {
    const updatedFilters = { ...filters, ...newFilters }
    setFilters(updatedFilters)
    debouncedSearch(updatedFilters)
  }

  const resetFilters = () => {
    setFilters(initialFilters)
    setHashtagInput('')
    onSearch('')
    onFiltersChange(initialFilters)
  }

  const addHashtag = () => {
    if (hashtagInput.trim()) {
      const hashtag = hashtagInput.trim().replace('#', '')
      const currentHashtags = filters.hashtags || []

      if (!currentHashtags.includes(hashtag)) {
        updateFilters({
          hashtags: [...currentHashtags, hashtag],
        })
      }
      setHashtagInput('')
    }
  }

  const removeHashtag = (hashtag: string) => {
    updateFilters({
      hashtags: (filters.hashtags || []).filter(h => h !== hashtag),
    })
  }

  const hasActiveFilters = () => {
    return (
      filters.query ||
      filters.dateFrom ||
      filters.dateTo ||
      filters.username ||
      filters.hasMedia !== undefined ||
      filters.hasArticles !== undefined ||
      filters.minEngagement ||
      (filters.hashtags && filters.hashtags.length > 0)
    )
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* メイン検索バー */}
      <div className="flex space-x-3">
        <div className="flex-1">
          <Input
            type="text"
            placeholder="ツイートを検索..."
            value={filters.query}
            onChange={e => updateFilters({ query: e.target.value })}
            leftIcon={<MagnifyingGlassIcon className="w-4 h-4" />}
            rightIcon={
              filters.query ? (
                <button
                  onClick={() => updateFilters({ query: '' })}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <XMarkIcon className="w-4 h-4" />
                </button>
              ) : null
            }
          />
        </div>

        <Button
          variant="outline"
          icon={<FunnelIcon className="w-4 h-4" />}
          onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
          className={showAdvancedFilters ? 'bg-blue-50 border-blue-200' : ''}
        >
          フィルタ
          {hasActiveFilters() && (
            <span className="ml-1 bg-blue-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
              !
            </span>
          )}
        </Button>

        {hasActiveFilters() && (
          <Button
            variant="outline"
            size="sm"
            onClick={resetFilters}
            className="text-red-600 hover:text-red-700"
          >
            リセット
          </Button>
        )}
      </div>

      {/* 詳細フィルタ */}
      {showAdvancedFilters && (
        <Card className="p-6">
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* 日付範囲 */}
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">期間</label>
                <div className="space-y-2">
                  <Input
                    type="date"
                    placeholder="開始日"
                    value={filters.dateFrom || ''}
                    onChange={e => updateFilters({ dateFrom: e.target.value || undefined })}
                  />
                  <Input
                    type="date"
                    placeholder="終了日"
                    value={filters.dateTo || ''}
                    onChange={e => updateFilters({ dateTo: e.target.value || undefined })}
                  />
                </div>
              </div>

              {/* ユーザー */}
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">ユーザー</label>
                <Input
                  type="text"
                  placeholder="@username"
                  value={filters.username || ''}
                  onChange={e => updateFilters({ username: e.target.value || undefined })}
                />
              </div>

              {/* 最小エンゲージメント */}
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">
                  最小エンゲージメント
                </label>
                <Input
                  type="number"
                  placeholder="例: 10"
                  value={filters.minEngagement?.toString() || ''}
                  onChange={e =>
                    updateFilters({
                      minEngagement: e.target.value ? Number(e.target.value) : undefined,
                    })
                  }
                />
              </div>
            </div>

            {/* メディア・記事フィルタ */}
            <div className="space-y-3">
              <label className="block text-sm font-medium text-gray-700">コンテンツタイプ</label>
              <div className="flex flex-wrap gap-4">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={filters.hasMedia === true}
                    onChange={e =>
                      updateFilters({
                        hasMedia: e.target.checked ? true : undefined,
                      })
                    }
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">メディア付き</span>
                </label>

                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={filters.hasArticles === true}
                    onChange={e =>
                      updateFilters({
                        hasArticles: e.target.checked ? true : undefined,
                      })
                    }
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">記事リンク付き</span>
                </label>
              </div>
            </div>

            {/* ハッシュタグ */}
            <div className="space-y-3">
              <label className="block text-sm font-medium text-gray-700">ハッシュタグ</label>
              <div className="flex space-x-2">
                <Input
                  type="text"
                  placeholder="#hashtag"
                  value={hashtagInput}
                  onChange={e => setHashtagInput(e.target.value)}
                  onKeyPress={e => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      addHashtag()
                    }
                  }}
                  className="flex-1"
                />
                <Button type="button" onClick={addHashtag} size="sm" variant="outline">
                  追加
                </Button>
              </div>

              {filters.hashtags && filters.hashtags.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {filters.hashtags.map(hashtag => (
                    <span
                      key={hashtag}
                      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                    >
                      #{hashtag}
                      <button
                        onClick={() => removeHashtag(hashtag)}
                        className="ml-1.5 text-blue-400 hover:text-blue-600"
                      >
                        <XMarkIcon className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* 並び替え */}
            <div className="space-y-3">
              <label className="block text-sm font-medium text-gray-700">並び替え</label>
              <div className="flex space-x-4">
                <select
                  value={filters.sortBy}
                  onChange={e =>
                    updateFilters({ sortBy: e.target.value as TweetFilters['sortBy'] })
                  }
                  className="block rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
                >
                  <option value="date">投稿日時</option>
                  <option value="engagement">エンゲージメント</option>
                  <option value="relevance">関連度</option>
                </select>

                <select
                  value={filters.sortOrder}
                  onChange={e =>
                    updateFilters({ sortOrder: e.target.value as TweetFilters['sortOrder'] })
                  }
                  className="block rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
                >
                  <option value="desc">降順</option>
                  <option value="asc">昇順</option>
                </select>
              </div>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}
