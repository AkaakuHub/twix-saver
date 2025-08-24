/**
 * APIクライアント
 * FastAPIバックエンドとの通信を担当
 */

import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios'
import { ApiError } from '../types'

const API_BASE_URL =
  (import.meta as { env?: Record<string, string> }).env?.VITE_API_BASE_URL ||
  'http://localhost:8000/api'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // リクエストインターセプター
    this.client.interceptors.request.use(
      config => {
        // 認証トークンがあれば追加（将来の実装用）
        // const token = localStorage.getItem('auth_token');
        // if (token) {
        //   config.headers.Authorization = `Bearer ${token}`;
        // }

        console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`)
        return config
      },
      error => Promise.reject(error)
    )

    // レスポンスインターセプター
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        console.log(`✅ API Response: ${response.status} ${response.config.url}`)
        return response
      },
      (error: AxiosError) => {
        console.error(
          `❌ API Error: ${error.response?.status} ${error.config?.url}`,
          error.response?.data
        )
        return this.handleApiError(error)
      }
    )
  }

  private handleApiError(error: AxiosError): Promise<never> {
    const response = error.response

    if (!response) {
      // ネットワークエラーまたはタイムアウト
      throw new ApiError('ネットワークエラーまたはサーバーに接続できません', 0, 'NETWORK_ERROR')
    }

    const data = response.data as Record<string, unknown>
    const message =
      typeof data?.message === 'string'
        ? data.message
        : typeof data?.detail === 'string'
          ? data.detail
          : 'APIエラーが発生しました'
    const errorCode = typeof data?.error_code === 'string' ? data.error_code : 'API_ERROR'

    throw new ApiError(
      message,
      response.status,
      errorCode,
      data?.details as Record<string, unknown> | undefined
    )
  }

  // 汎用HTTPメソッド
  async get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
    const response = await this.client.get<T>(url, { params })
    return response.data
  }

  async post<T>(url: string, data?: unknown): Promise<T> {
    const response = await this.client.post<T>(url, data)
    return response.data
  }

  async put<T>(url: string, data?: unknown): Promise<T> {
    const response = await this.client.put<T>(url, data)
    return response.data
  }

  async patch<T>(url: string, data?: unknown): Promise<T> {
    const response = await this.client.patch<T>(url, data)
    return response.data
  }

  async delete<T>(url: string): Promise<T> {
    const response = await this.client.delete<T>(url)
    return response.data
  }

  // ヘルスチェック
  async healthCheck() {
    return this.get('/health')
  }

  // WebSocket URLを取得
  getWebSocketUrl(): string {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsHost =
      (import.meta as { env?: Record<string, string> }).env?.VITE_API_HOST || 'localhost:8000'
    return `${wsProtocol}//${wsHost}/api/ws`
  }
}

// シングルトンインスタンス
export const apiClient = new ApiClient()
export default apiClient
