/**
 * 日時フォーマット関数
 * JST（日本標準時）での年月日時分秒ミリ秒表示
 */

import { format, toZonedTime } from 'date-fns-tz'

const JST_TIMEZONE = 'Asia/Tokyo'

/**
 * 日付をJSTの年月日時分秒ミリ秒形式でフォーマット
 * 例: 2025-08-25 21:30:45.123
 */
export const formatDateTimeJST = (date: string | Date): string => {
  const dateObj = typeof date === 'string' ? new Date(date) : date
  const jstDate = toZonedTime(dateObj, JST_TIMEZONE)
  return format(jstDate, 'yyyy-MM-dd HH:mm:ss.SSS', { timeZone: JST_TIMEZONE })
}

/**
 * ツイート作成時刻用フォーマット（年月日時分秒ミリ秒）
 */
export const formatTweetCreatedAt = (date: string): string => {
  return formatDateTimeJST(date)
}

/**
 * スクレイピング時刻用フォーマット（年月日時分秒ミリ秒）
 */
export const formatScrapedAt = (date: string): string => {
  return formatDateTimeJST(date)
}

/**
 * ユーザー作成時刻など（年月日時分）
 * 例: 2025/08/25 21:30
 */
export const formatUserDateTime = (date: string | Date | null | undefined): string => {
  if (!date) return '-'
  const dateObj = typeof date === 'string' ? new Date(date) : date
  const jstDate = toZonedTime(dateObj, JST_TIMEZONE)
  return format(jstDate, 'yyyy/MM/dd HH:mm', { timeZone: JST_TIMEZONE })
}

/**
 * ジョブ作成日時など（年月日時分秒）
 * 例: 2025/08/25 21:30:45
 */
export const formatJobDateTime = (date: string | Date): string => {
  const dateObj = typeof date === 'string' ? new Date(date) : date
  const jstDate = toZonedTime(dateObj, JST_TIMEZONE)
  return format(jstDate, 'yyyy/MM/dd HH:mm:ss', { timeZone: JST_TIMEZONE })
}

/**
 * 日付のみ表示（年月日）
 * 例: 2025/08/25
 */
export const formatDateOnly = (date: string | Date): string => {
  const dateObj = typeof date === 'string' ? new Date(date) : date
  const jstDate = toZonedTime(dateObj, JST_TIMEZONE)
  return format(jstDate, 'yyyy/MM/dd', { timeZone: JST_TIMEZONE })
}
