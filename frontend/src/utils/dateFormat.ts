/**
 * 日時フォーマット関数
 * JST（日本標準時）での年月日時分秒ミリ秒表示
 * バックエンドからのUTC時刻を適切に変換
 */

import { format, toZonedTime } from 'date-fns-tz'

const JST_TIMEZONE = 'Asia/Tokyo'

/**
 * UTC時刻文字列をUTCとして解析
 */
function parseUtcDate(date: string | Date): Date {
  if (typeof date !== 'string') return date

  // 'Z'やタイムゾーン情報がない場合はUTCとして扱う
  const dateString =
    date.includes('Z') || date.includes('+') || date.includes('-', 10) ? date : date + 'Z'
  return new Date(dateString)
}

/**
 * 日付をJSTの年月日時分秒ミリ秒形式でフォーマット
 * 例: 2025-08-25 21:30:45.123
 */
export const formatDateTimeJST = (date: string | Date): string => {
  if (!date) return '-'

  const dateObj = parseUtcDate(date)

  // 無効な日時値をチェック
  if (isNaN(dateObj.getTime())) {
    console.warn('Invalid date value:', date)
    return '-'
  }

  const jstDate = toZonedTime(dateObj, JST_TIMEZONE)
  return format(jstDate, 'yyyy-MM-dd HH:mm:ss.SSS', { timeZone: JST_TIMEZONE })
}

/**
 * ツイート作成時刻用フォーマット（年月日時分秒ミリ秒）
 */
export const formatTweetCreatedAt = (date: string | null | undefined): string => {
  if (!date) return '-'
  return formatDateTimeJST(date)
}

/**
 * スクレイピング時刻用フォーマット（年月日時分秒ミリ秒）
 */
export const formatScrapedAt = (date: string | null | undefined): string => {
  if (!date) return '-'
  return formatDateTimeJST(date)
}

/**
 * ユーザー作成時刻など（年月日時分）
 * 例: 2025/08/25 21:30
 */
export const formatUserDateTime = (date: string | Date | null | undefined): string => {
  if (!date) return '-'
  const dateObj = parseUtcDate(date)

  // 無効な日時値をチェック
  if (isNaN(dateObj.getTime())) {
    console.warn('Invalid date value:', date)
    return '-'
  }

  const jstDate = toZonedTime(dateObj, JST_TIMEZONE)
  return format(jstDate, 'yyyy/MM/dd HH:mm', { timeZone: JST_TIMEZONE })
}

/**
 * ジョブ作成日時など（年月日時分秒）
 * 例: 2025/08/25 21:30:45
 * 注意: バックエンドからのUTC時刻をJSTに変換
 */
export const formatJobDateTime = (date: string | Date | null | undefined): string => {
  if (!date) return '-'

  const dateObj = parseUtcDate(date)

  // 無効な日時値をチェック
  if (isNaN(dateObj.getTime())) {
    console.warn('Invalid date value:', date)
    return '-'
  }

  const jstDate = toZonedTime(dateObj, JST_TIMEZONE)
  return format(jstDate, 'yyyy/MM/dd HH:mm:ss', { timeZone: JST_TIMEZONE })
}

/**
 * 日付のみ表示（年月日）
 * 例: 2025/08/25
 */
export const formatDateOnly = (date: string | Date): string => {
  const dateObj = parseUtcDate(date)

  // 無効な日時値をチェック
  if (isNaN(dateObj.getTime())) {
    console.warn('Invalid date value:', date)
    return '-'
  }

  const jstDate = toZonedTime(dateObj, JST_TIMEZONE)
  return format(jstDate, 'yyyy/MM/dd', { timeZone: JST_TIMEZONE })
}
