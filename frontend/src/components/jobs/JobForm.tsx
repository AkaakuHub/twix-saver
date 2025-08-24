import { useState } from 'react'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { XMarkIcon } from '@heroicons/react/24/outline'
import type { ScrapingJobCreate } from '../../types/api'

interface JobFormProps {
  onSubmit: (jobData: ScrapingJobCreate) => void
  onCancel: () => void
  isSubmitting?: boolean
}

export const JobForm = ({ onSubmit, onCancel, isSubmitting = false }: JobFormProps) => {
  const [targetUsernames, setTargetUsernames] = useState<string[]>([])
  const [usernameInput, setUsernameInput] = useState('')
  const [processArticles, setProcessArticles] = useState(false)
  const [maxTweets, setMaxTweets] = useState<number | undefined>(undefined)

  const addUsername = () => {
    const username = usernameInput.trim()
    if (username && !targetUsernames.includes(username)) {
      setTargetUsernames([...targetUsernames, username])
      setUsernameInput('')
    }
  }

  const removeUsername = (username: string) => {
    setTargetUsernames(targetUsernames.filter(u => u !== username))
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addUsername()
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (targetUsernames.length === 0) return

    onSubmit({
      target_usernames: targetUsernames,
      process_articles: processArticles,
      max_tweets: maxTweets || null,
    })
  }

  return (
    <Card className="w-full max-w-2xl">
      <CardHeader>
        <CardTitle>新規ジョブ作成</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* ターゲットユーザー */}
          <div className="space-y-3">
            <label className="block text-sm font-medium text-gray-700">対象Twitterユーザー</label>
            <div className="flex gap-2">
              <Input
                type="text"
                placeholder="@username (@ は不要)"
                value={usernameInput}
                onChange={e => setUsernameInput(e.target.value)}
                onKeyPress={handleKeyPress}
                className="flex-1"
              />
              <Button type="button" onClick={addUsername} disabled={!usernameInput.trim()}>
                追加
              </Button>
            </div>

            {/* 追加されたユーザー名の表示 */}
            {targetUsernames.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {targetUsernames.map(username => (
                  <Badge key={username} variant="default" className="flex items-center gap-1">
                    @{username}
                    <button
                      type="button"
                      onClick={() => removeUsername(username)}
                      className="ml-1 hover:text-red-500"
                    >
                      <XMarkIcon className="w-3 h-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            )}
          </div>

          {/* 記事処理オプション */}
          <div className="flex items-center space-x-3">
            <input
              type="checkbox"
              id="processArticles"
              checked={processArticles}
              onChange={e => setProcessArticles(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="processArticles" className="text-sm text-gray-700">
              記事の内容を抽出する
            </label>
          </div>

          {/* 最大ツイート数 */}
          <div className="space-y-2">
            <label htmlFor="maxTweets" className="block text-sm font-medium text-gray-700">
              最大ツイート数 (空欄の場合は制限なし)
            </label>
            <Input
              type="number"
              id="maxTweets"
              min="1"
              max="10000"
              value={maxTweets || ''}
              onChange={e => setMaxTweets(e.target.value ? Number(e.target.value) : undefined)}
              placeholder="例: 100"
            />
          </div>

          {/* ボタン */}
          <div className="flex justify-end space-x-3">
            <Button type="button" variant="outline" onClick={onCancel} disabled={isSubmitting}>
              キャンセル
            </Button>
            <Button
              type="submit"
              disabled={targetUsernames.length === 0 || isSubmitting}
              loading={isSubmitting}
            >
              ジョブを作成
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
