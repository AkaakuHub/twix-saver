import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/Card'
import { Input } from '../ui/Input'
import { Label } from '../ui/label'
import { Button } from '../ui/Button'
import { Switch } from '../ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs'
import { Separator } from '../ui/separator'
import { Alert, AlertDescription } from '../ui/alert'
import { Save, RefreshCw } from 'lucide-react'
import { apiClient as api } from '../../services/api'
import { SettingsResponse, SettingsRequest, TwitterAccount } from '../../types/settings'

const defaultSettings: SettingsResponse = {
  proxy: {
    enabled: false,
    server: '',
    username: '',
    password: '',
  },
  scraping: {
    intervalMinutes: 15,
    randomDelayMaxSeconds: 120,
    maxTweetsPerSession: 100,
    headless: true,
  },
  general: {
    logLevel: 'INFO',
    corsOrigins: 'http://localhost:3000,http://localhost:5173',
  },
  twitter_accounts_available: 0,
}

export function Settings() {
  const [settings, setSettings] = useState<SettingsResponse>(defaultSettings)
  const [twitterAccounts, setTwitterAccounts] = useState<TwitterAccount[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [showAccountForm, setShowAccountForm] = useState(false)
  const [newAccount, setNewAccount] = useState({
    username: '',
    email: '',
    password: '',
    display_name: '',
    notes: '',
  })

  useEffect(() => {
    loadSettings()
    loadTwitterAccounts()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 設定データを安全にマージする関数（型安全性を保証）
  const mergeSettings = (apiData: unknown): SettingsResponse => {
    // APIデータの構造を検証
    if (!apiData || typeof apiData !== 'object') {
      console.warn('APIデータが無効です。デフォルト設定を使用します。', apiData)
      return defaultSettings
    }

    const data = apiData as Record<string, Record<string, unknown>>

    return {
      proxy: {
        enabled: Boolean(data.proxy?.enabled ?? defaultSettings.proxy.enabled),
        server: String(data.proxy?.server ?? defaultSettings.proxy.server),
        username: String(data.proxy?.username ?? defaultSettings.proxy.username),
        password: String(data.proxy?.password ?? defaultSettings.proxy.password),
      },
      scraping: {
        intervalMinutes: Number(
          data.scraping?.intervalMinutes ?? defaultSettings.scraping.intervalMinutes
        ),
        randomDelayMaxSeconds: Number(
          data.scraping?.randomDelayMaxSeconds ?? defaultSettings.scraping.randomDelayMaxSeconds
        ),
        maxTweetsPerSession: Number(
          data.scraping?.maxTweetsPerSession ?? defaultSettings.scraping.maxTweetsPerSession
        ),
        headless: Boolean(data.scraping?.headless ?? defaultSettings.scraping.headless),
      },
      general: {
        logLevel: String(data.general?.logLevel ?? defaultSettings.general.logLevel),
        corsOrigins: String(data.general?.corsOrigins ?? defaultSettings.general.corsOrigins),
      },
      twitter_accounts_available: Number(
        (data as Record<string, unknown>).twitter_accounts_available ??
          defaultSettings.twitter_accounts_available
      ),
    }
  }

  const loadSettings = async () => {
    try {
      setLoading(true)
      const response = await api.get('/settings')

      const mergedSettings = mergeSettings(response)
      setSettings(mergedSettings)
    } catch {
      setMessage({ type: 'error', text: '設定の読み込みに失敗しました' })
    } finally {
      setLoading(false)
    }
  }

  const loadTwitterAccounts = async () => {
    try {
      const response = await api.get('/accounts')
      setTwitterAccounts(response as TwitterAccount[])
    } catch {
      // Twitterアカウント読み込みエラーは無視
    }
  }

  const saveSettings = async () => {
    try {
      setSaving(true)

      // APIリクエスト用のデータ（twitter_accounts_availableは除外）
      const requestData: SettingsRequest = {
        proxy: settings.proxy,
        scraping: settings.scraping,
        general: settings.general,
      }

      await api.put('/settings', requestData)
      setMessage({ type: 'success', text: '設定を保存しました' })
      setTimeout(() => setMessage(null), 3000)
    } catch {
      setMessage({ type: 'error', text: '設定の保存に失敗しました' })
    } finally {
      setSaving(false)
    }
  }

  const updateSettings = (section: keyof SettingsResponse, key: string, value: unknown) => {
    setSettings(prev => ({
      ...prev,
      [section]: {
        ...(prev[section] as object),
        [key]: value,
      },
    }))
  }

  const createTwitterAccount = async () => {
    try {
      await api.post('/accounts', newAccount)
      setMessage({ type: 'success', text: 'Twitterアカウントを追加しました' })
      setShowAccountForm(false)
      setNewAccount({
        username: '',
        email: '',
        password: '',
        display_name: '',
        notes: '',
      })
      await loadTwitterAccounts()
      setTimeout(() => setMessage(null), 3000)
    } catch (error: unknown) {
      setMessage({
        type: 'error',
        text: (error as Error).message || 'アカウント作成に失敗しました',
      })
    }
  }

  const deleteTwitterAccount = async (accountId: string) => {
    if (!confirm('このアカウントを削除してもよろしいですか？')) return

    try {
      await api.delete(`/accounts/${accountId}`)
      setMessage({ type: 'success', text: 'Twitterアカウントを削除しました' })
      await loadTwitterAccounts()
      setTimeout(() => setMessage(null), 3000)
    } catch (error: unknown) {
      setMessage({
        type: 'error',
        text: (error as Error).message || 'アカウント削除に失敗しました',
      })
    }
  }

  const toggleAccountActive = async (accountId: string, active: boolean) => {
    try {
      if (active) {
        await api.post(`/accounts/${accountId}/activate`)
      } else {
        await api.post(`/accounts/${accountId}/deactivate`)
      }
      await loadTwitterAccounts()
    } catch (error: unknown) {
      setMessage({
        type: 'error',
        text: (error as Error).message || 'アカウント状態変更に失敗しました',
      })
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="container max-w-4xl py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">設定</h1>
          <p className="text-muted-foreground">アプリケーションの設定を管理します</p>
        </div>
        <Button onClick={saveSettings} disabled={saving}>
          <Save className="w-4 h-4 mr-2" />
          {saving ? '保存中...' : '保存'}
        </Button>
      </div>

      {message && (
        <Alert variant={message.type === 'error' ? 'destructive' : 'default'}>
          <AlertDescription>{message.text}</AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="accounts" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="accounts">アカウント</TabsTrigger>
          <TabsTrigger value="proxy">プロキシ</TabsTrigger>
          <TabsTrigger value="scraping">スクレイピング</TabsTrigger>
          <TabsTrigger value="general">一般</TabsTrigger>
        </TabsList>

        <TabsContent value="accounts">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Twitterアカウント管理</CardTitle>
                  <CardDescription>
                    スクレイピングに使用するTwitterアカウントを管理します（{twitterAccounts.length}
                    個のアカウント）
                  </CardDescription>
                </div>
                <Button onClick={() => setShowAccountForm(true)}>アカウント追加</Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {showAccountForm && (
                <Card className="border-dashed">
                  <CardHeader>
                    <CardTitle className="text-lg">新しいTwitterアカウントを追加</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="new-username">ユーザー名</Label>
                        <Input
                          id="new-username"
                          value={newAccount.username}
                          onChange={e => setNewAccount({ ...newAccount, username: e.target.value })}
                          placeholder="@username"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="new-email">メールアドレス</Label>
                        <Input
                          id="new-email"
                          type="email"
                          value={newAccount.email}
                          onChange={e => setNewAccount({ ...newAccount, email: e.target.value })}
                          placeholder="email@example.com"
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="new-password">パスワード</Label>
                      <Input
                        id="new-password"
                        type="password"
                        value={newAccount.password}
                        onChange={e => setNewAccount({ ...newAccount, password: e.target.value })}
                        placeholder="パスワードを入力"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="new-display-name">表示名（オプション）</Label>
                        <Input
                          id="new-display-name"
                          value={newAccount.display_name}
                          onChange={e =>
                            setNewAccount({ ...newAccount, display_name: e.target.value })
                          }
                          placeholder="表示名"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="new-notes">メモ（オプション）</Label>
                        <Input
                          id="new-notes"
                          value={newAccount.notes}
                          onChange={e => setNewAccount({ ...newAccount, notes: e.target.value })}
                          placeholder="メモ"
                        />
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button onClick={createTwitterAccount}>追加</Button>
                      <Button variant="outline" onClick={() => setShowAccountForm(false)}>
                        キャンセル
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}

              {twitterAccounts.length > 0 ? (
                <div className="space-y-2">
                  {twitterAccounts.map(account => (
                    <Card key={account.account_id} className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                          <div>
                            <div className="font-medium">@{account.username}</div>
                            <div className="text-sm text-gray-500">{account.email}</div>
                            {account.display_name && (
                              <div className="text-sm text-gray-600">{account.display_name}</div>
                            )}
                          </div>
                          <div className="text-sm">
                            <div
                              className={`inline-flex px-2 py-1 rounded text-xs ${
                                account.status === 'active'
                                  ? 'bg-green-100 text-green-800'
                                  : account.status === 'inactive'
                                    ? 'bg-gray-100 text-gray-800'
                                    : account.status === 'rate_limited'
                                      ? 'bg-yellow-100 text-yellow-800'
                                      : 'bg-red-100 text-red-800'
                              }`}
                            >
                              {account.status}
                            </div>
                            <div className="mt-1">
                              成功: {account.successful_jobs} / 失敗: {account.failed_jobs}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Switch
                            checked={account.active}
                            onCheckedChange={checked =>
                              toggleAccountActive(account.account_id, checked)
                            }
                          />
                          <Button
                            variant="danger"
                            size="sm"
                            onClick={() => deleteTwitterAccount(account.account_id)}
                          >
                            削除
                          </Button>
                        </div>
                      </div>
                      {account.notes && (
                        <div className="mt-2 text-sm text-gray-600 border-t pt-2">
                          {account.notes}
                        </div>
                      )}
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  Twitterアカウントが登録されていません
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="proxy">
          <Card>
            <CardHeader>
              <CardTitle>プロキシ設定</CardTitle>
              <CardDescription>匿名性向上のためのプロキシサーバー設定</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center space-x-2">
                <Switch
                  id="proxy-enabled"
                  checked={settings.proxy.enabled}
                  onCheckedChange={checked => updateSettings('proxy', 'enabled', checked)}
                />
                <Label htmlFor="proxy-enabled">プロキシを使用する</Label>
              </div>

              {settings.proxy.enabled && (
                <>
                  <Separator />
                  <div className="space-y-2">
                    <Label htmlFor="proxy-server">プロキシサーバー</Label>
                    <Input
                      id="proxy-server"
                      value={settings.proxy.server}
                      onChange={e => updateSettings('proxy', 'server', e.target.value)}
                      placeholder="proxy.example.com:8080"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="proxy-username">ユーザー名（オプション）</Label>
                    <Input
                      id="proxy-username"
                      value={settings.proxy.username}
                      onChange={e => updateSettings('proxy', 'username', e.target.value)}
                      placeholder="プロキシのユーザー名"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="proxy-password">パスワード（オプション）</Label>
                    <Input
                      id="proxy-password"
                      type="password"
                      value={settings.proxy.password}
                      onChange={e => updateSettings('proxy', 'password', e.target.value)}
                      placeholder="プロキシのパスワード"
                    />
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="scraping">
          <Card>
            <CardHeader>
              <CardTitle>スクレイピング設定</CardTitle>
              <CardDescription>データ収集の頻度や制限を設定します</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="interval-minutes">実行間隔（分）</Label>
                <Input
                  id="interval-minutes"
                  type="number"
                  min="1"
                  value={settings.scraping.intervalMinutes}
                  onChange={e =>
                    updateSettings('scraping', 'intervalMinutes', parseInt(e.target.value) || 1)
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="random-delay">ランダム遅延最大値（秒）</Label>
                <Input
                  id="random-delay"
                  type="number"
                  min="0"
                  value={settings.scraping.randomDelayMaxSeconds}
                  onChange={e =>
                    updateSettings(
                      'scraping',
                      'randomDelayMaxSeconds',
                      parseInt(e.target.value) || 0
                    )
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="max-tweets">セッションあたり最大ツイート数</Label>
                <Input
                  id="max-tweets"
                  type="number"
                  min="1"
                  value={settings.scraping.maxTweetsPerSession}
                  onChange={e =>
                    updateSettings('scraping', 'maxTweetsPerSession', parseInt(e.target.value) || 1)
                  }
                />
              </div>
              <div className="flex items-center space-x-2">
                <Switch
                  id="headless"
                  checked={settings.scraping.headless}
                  onCheckedChange={checked => updateSettings('scraping', 'headless', checked)}
                />
                <Label htmlFor="headless">ヘッドレスモード（ブラウザを非表示）</Label>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="general">
          <Card>
            <CardHeader>
              <CardTitle>一般設定</CardTitle>
              <CardDescription>アプリケーション全体の設定</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="log-level">ログレベル</Label>
                <select
                  id="log-level"
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                  value={settings.general.logLevel}
                  onChange={e => updateSettings('general', 'logLevel', e.target.value)}
                >
                  <option value="DEBUG">DEBUG</option>
                  <option value="INFO">INFO</option>
                  <option value="WARNING">WARNING</option>
                  <option value="ERROR">ERROR</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="cors-origins">CORS許可オリジン</Label>
                <Input
                  id="cors-origins"
                  value={settings.general.corsOrigins}
                  onChange={e => updateSettings('general', 'corsOrigins', e.target.value)}
                  placeholder="http://localhost:3000,http://localhost:5173"
                />
                <p className="text-sm text-muted-foreground">カンマ区切りで複数指定可能</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
