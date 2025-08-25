/**
 * 設定関連の型定義 - バックエンドと統一
 */

export interface ProxyConfig {
  enabled: boolean
  server: string
  username: string
  password: string
}

export interface ScrapingConfig {
  intervalMinutes: number
  randomDelayMaxSeconds: number
  maxTweetsPerSession: number
  headless: boolean
}

export interface GeneralConfig {
  logLevel: string
}

// バックエンドのSettingsResponseと完全に一致する型
export interface SettingsResponse {
  proxy: ProxyConfig
  scraping: ScrapingConfig
  general: GeneralConfig
  twitter_accounts_available: number
}

// 設定更新リクエスト用の型
export interface SettingsRequest {
  proxy: ProxyConfig
  scraping: ScrapingConfig
  general: GeneralConfig
}

// Twitterアカウント関連の型
export interface TwitterAccount {
  account_id: string
  username: string
  email: string
  display_name?: string
  status: string
  active: boolean
  created_at?: string
  updated_at?: string
  total_jobs_run: number
  successful_jobs: number
  failed_jobs: number
  notes?: string
}
