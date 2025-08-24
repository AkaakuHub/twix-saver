import { useState, useEffect } from 'react'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { XMarkIcon, InformationCircleIcon } from '@heroicons/react/24/outline'
import type { ScrapingJobCreate } from '../../types/api'
import { apiClient } from '../../services/api'

interface JobFormProps {
  onSubmit: (jobData: ScrapingJobCreate) => void
  onCancel: () => void
  isSubmitting?: boolean
}

interface TwitterAccount {
  username: string
  display_name?: string
  active: boolean
}

export const JobForm = ({ onSubmit, onCancel, isSubmitting = false }: JobFormProps) => {
  const [targetUsernames, setTargetUsernames] = useState<string[]>([])
  const [usernameInput, setUsernameInput] = useState('')
  const [processArticles, setProcessArticles] = useState(false)
  const [maxTweets, setMaxTweets] = useState<number | undefined>(undefined)
  const [availableAccounts, setAvailableAccounts] = useState<TwitterAccount[]>([])
  const [selectedAccount, setSelectedAccount] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const addUsername = () => {
    const username = usernameInput.trim()
    if (username && !targetUsernames.includes(username)) {
      setTargetUsernames([...targetUsernames, username])
      setUsernameInput('')
      setError(null) // エラーをクリア
    }
  }

  const removeUsername = (username: string) => {
    setTargetUsernames(targetUsernames.filter(u => u !== username))
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addUsername()
    }
  }

  useEffect(() => {
    loadAvailableAccounts()
  }, [])

  const loadAvailableAccounts = async () => {
    try {
      setLoading(true)
      const accounts = await apiClient.get<TwitterAccount[]>('/accounts?available_only=true')
      setAvailableAccounts(accounts)
      if (accounts.length === 1) {
        setSelectedAccount(accounts[0].username)
      }
    } catch {
      setError('アカウント情報の取得に失敗しました')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (targetUsernames.length === 0) {
      setError('少なくとも1人のターゲットユーザーを指定してください')
      return
    }
    if (!selectedAccount) {
      setError('スクレイピング用アカウントを選択してください')
      return
    }

    onSubmit({
      target_usernames: targetUsernames,
      process_articles: processArticles,
      max_tweets: maxTweets || null,
      scraper_account: selectedAccount,
    })
  }

  return (
    <Card className="w-full max-w-2xl">
      <CardHeader>
        <CardTitle>新規ジョブ作成</CardTitle>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
            <div className="flex items-center">
              <InformationCircleIcon className="w-5 h-5 text-red-400 mr-2" />
              <span className="text-sm text-red-700">{error}</span>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* スクレイピング用アカウント選択 */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              スクレイピング用Twitterアカウント
            </label>
            <select
              value={selectedAccount}
              onChange={e => setSelectedAccount(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              disabled={loading || availableAccounts.length === 0}
            >
              <option value="">アカウントを選択...</option>
              {availableAccounts.map(account => (
                <option key={account.username} value={account.username}>
                  @{account.username}
                  {account.display_name && ` (${account.display_name})`}
                </option>
              ))}
            </select>
            {availableAccounts.length === 0 && !loading && (
              <p className="text-sm text-amber-600">
                利用可能なアカウントがありません。設定画面でTwitterアカウントを追加してください。
              </p>
            )}
          </div>

          {/* ターゲットユーザー */}
          <div className="space-y-3">
            <label className="block text-sm font-medium text-gray-700">
              監視対象ユーザー（第三者のTwitterアカウント）
            </label>
            <div className="p-3 bg-green-50 border border-green-200 rounded-md">
              <p className="text-sm text-green-700">
                任意のTwitterユーザー名を入力してください（例：elonmusk,
                taylorswift13など）。事前登録は不要です。
              </p>
            </div>
            <div className="flex gap-2">
              <Input
                type="text"
                placeholder="@username (@ は不要)"
                value={usernameInput}
                onChange={e => setUsernameInput(e.target.value)}
                onKeyDown={handleKeyDown}
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
