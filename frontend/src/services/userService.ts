/**
 * ユーザー管理サービス
 * ターゲットユーザーのCRUD操作を提供
 */

import { apiClient } from './api'
import type {
  TargetUser,
  TargetUserCreate,
  TargetUserUpdate,
  UserStatistics,
  SuccessResponse,
} from '@/types/api'

export class UserService {
  // ユーザー一覧取得
  async getUsers(includeInactive = false, search?: string): Promise<TargetUser[]> {
    const params: Record<string, unknown> = { include_inactive: includeInactive }
    if (search) {
      params.search = search
    }

    return apiClient.get<TargetUser[]>('/users', params)
  }

  // アクティブユーザーのみ取得
  async getActiveUsers(): Promise<TargetUser[]> {
    return apiClient.get<TargetUser[]>('/users/active')
  }

  // 特定ユーザー取得
  async getUser(username: string): Promise<TargetUser> {
    return apiClient.get<TargetUser>(`/users/${username}`)
  }

  // ユーザー作成
  async createUser(userData: TargetUserCreate): Promise<SuccessResponse> {
    return apiClient.post<SuccessResponse>('/users', userData)
  }

  // ユーザー更新
  async updateUser(username: string, userData: TargetUserUpdate): Promise<SuccessResponse> {
    return apiClient.put<SuccessResponse>(`/users/${username}`, userData)
  }

  // ユーザー削除
  async deleteUser(username: string): Promise<SuccessResponse> {
    return apiClient.delete<SuccessResponse>(`/users/${username}`)
  }

  // ユーザー有効化
  async activateUser(username: string): Promise<SuccessResponse> {
    return apiClient.post<SuccessResponse>(`/users/${username}/activate`)
  }

  // ユーザー無効化
  async deactivateUser(username: string): Promise<SuccessResponse> {
    return apiClient.post<SuccessResponse>(`/users/${username}/deactivate`)
  }

  // 優先度更新
  async updateUserPriority(username: string, priority: number): Promise<SuccessResponse> {
    return apiClient.put<SuccessResponse>(`/users/${username}/priority?priority=${priority}`)
  }

  // 優先度別ユーザー取得
  async getUsersByPriority(minPriority: number): Promise<TargetUser[]> {
    return apiClient.get<TargetUser[]>(`/users/priority/${minPriority}`)
  }

  // ユーザー統計取得
  async getUserStatistics(): Promise<UserStatistics> {
    return apiClient.get<UserStatistics>('/users/stats/summary')
  }

  // ユーザー検索
  async searchUsers(query: string): Promise<TargetUser[]> {
    return this.getUsers(true, query)
  }

  // バッチ操作用のヘルパーメソッド
  async bulkActivateUsers(usernames: string[]): Promise<SuccessResponse[]> {
    const promises = usernames.map(username => this.activateUser(username))
    return Promise.all(promises)
  }

  async bulkDeactivateUsers(usernames: string[]): Promise<SuccessResponse[]> {
    const promises = usernames.map(username => this.deactivateUser(username))
    return Promise.all(promises)
  }

  async bulkDeleteUsers(usernames: string[]): Promise<SuccessResponse[]> {
    const promises = usernames.map(username => this.deleteUser(username))
    return Promise.all(promises)
  }

  // ユーザー名の正規化（@記号を除去）
  normalizeUsername(username: string): string {
    return username.replace(/^@/, '').toLowerCase()
  }

  // ユーザーのアクティビティ状態を判定
  isUserActive(user: TargetUser): boolean {
    return user.active && user.scraping_enabled
  }

  // 最後のスクレイピングからの経過時間（分）
  getMinutesSinceLastScraping(user: TargetUser): number | null {
    if (!user.last_scraped_at) return null

    const lastScraped = new Date(user.last_scraped_at)
    const now = new Date()
    return Math.floor((now.getTime() - lastScraped.getTime()) / (1000 * 60))
  }

  // ユーザーの健全性スコアを計算
  getUserHealthScore(user: TargetUser): number {
    let score = 100

    // 非アクティブなら大幅減点
    if (!user.active) score -= 50
    if (!user.scraping_enabled) score -= 30

    // エラーがあるなら減点
    if (user.last_error) score -= 20

    // 長期間スクレイピングされていないなら減点
    const minutesSince = this.getMinutesSinceLastScraping(user)
    if (minutesSince) {
      if (minutesSince > 1440)
        score -= 15 // 1日以上
      else if (minutesSince > 120) score -= 5 // 2時間以上
    }

    return Math.max(0, score)
  }
}

// シングルトンインスタンス
export const userService = new UserService()
export default userService
