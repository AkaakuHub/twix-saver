import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { formatTweetCreatedAt, formatScrapedAt } from '../../utils/dateFormat'
import { ImageProcessingStatus } from '../../types/api'
import {
  HeartIcon,
  ArrowPathRoundedSquareIcon,
  ChatBubbleOvalLeftIcon,
  ArrowTopRightOnSquareIcon,
  PhotoIcon,
  DocumentTextIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  TrashIcon,
  ArrowPathIcon,
  EllipsisHorizontalIcon,
} from '@heroicons/react/24/outline'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { ImageModal } from '../ui/ImageModal'
import { BACKEND_URL } from '../../config/env'
import { clsx } from 'clsx'

interface Tweet {
  id: string
  text: string
  author: {
    username: string
    display_name: string
    profile_image_url?: string
  }
  created_at: string
  scraped_at?: string
  public_metrics: {
    like_count: number
    retweet_count: number
    reply_count: number
    quote_count: number
  }
  media?: Array<{
    type: 'photo' | 'video' | 'gif'
    url: string
    preview_image_url?: string
    width?: number
    height?: number
  }>
  downloaded_media?: Array<{
    media_id: string
    original_url: string
    type: 'photo' | 'linked_image'
    mime_type: string
    size: number
    local_url?: string
    position?: number
    order_type?: 'attachment' | 'link'
  }>
  extracted_articles?: Array<{
    title: string
    url: string
    description?: string
    image?: string
    domain?: string
  }>
  entities?: {
    hashtags?: Array<{ tag: string }>
    mentions?: Array<{ username: string }>
    urls?: Array<{ expanded_url: string; display_url: string }>
  }
  referenced_tweet?: {
    type: 'retweeted' | 'quoted' | 'replied_to'
    id: string
  }
  // 画像処理状態
  image_processing_status?: string
  image_processing_error?: string
  image_processing_retry_count?: number
  image_processing_completed_at?: string
}

interface TweetCardProps {
  tweet: Tweet
  expanded?: boolean
  onExpand?: (tweetId: string) => void
  onDelete?: (tweetId: string) => void
  onRefreshTweet?: (tweetId: string) => void
  className?: string
}

export const TweetCard = ({
  tweet,
  expanded = false,
  onExpand,
  onDelete,
  onRefreshTweet,
  className = '',
}: TweetCardProps) => {
  const [isExpanded, setIsExpanded] = useState(expanded)
  const [showActions, setShowActions] = useState(false)
  const [showLinkedImages, setShowLinkedImages] = useState(false)
  const [selectedImage, setSelectedImage] = useState<string | null>(null)
  const actionsRef = useRef<HTMLDivElement>(null)

  const toggleExpanded = () => {
    const newExpanded = !isExpanded
    setIsExpanded(newExpanded)
    onExpand?.(tweet.id)
  }

  const handleDelete = () => {
    if (confirm('このツイートを削除しますか？関連するメディアファイルも削除されます。')) {
      onDelete?.(tweet.id)
    }
  }

  const handleRefreshTweet = () => {
    onRefreshTweet?.(tweet.id)
    setShowActions(false)
  }

  // 画像処理ステータス表示用の関数
  const getImageProcessingBadge = () => {
    const status = tweet.image_processing_status
    if (!status || status === 'skipped') return null

    const statusConfig = {
      [ImageProcessingStatus.PENDING]: {
        icon: '📸⏸️',
        label: '未処理',
        variant: 'warning' as const,
      },
      [ImageProcessingStatus.PROCESSING]: {
        icon: '📸⏳',
        label: '処理中',
        variant: 'info' as const,
      },
      [ImageProcessingStatus.COMPLETED]: {
        icon: '📸✅',
        label: '完了',
        variant: 'success' as const,
      },
      [ImageProcessingStatus.FAILED]: {
        icon: '📸❌',
        label: '失敗',
        variant: 'error' as const,
      },
    }

    const config = statusConfig[status as keyof typeof statusConfig]
    if (!config) return null

    return (
      <Badge variant={config.variant} size="sm">
        {config.icon} {config.label}
      </Badge>
    )
  }

  // 外部クリック時にアクションメニューを閉じる
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (actionsRef.current && !actionsRef.current.contains(event.target as Node)) {
        setShowActions(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const formatNumber = useCallback((num: number) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
    return num.toString()
  }, [])

  const getTotalEngagement = useCallback(() => {
    const { like_count, retweet_count, reply_count, quote_count } = tweet.public_metrics
    return like_count + retweet_count + reply_count + quote_count
  }, [tweet.public_metrics])

  const renderText = useCallback((text: string) => {
    let formattedText = text

    // ハッシュタグをハイライト
    formattedText = formattedText.replace(
      /#(\w+)/g,
      '<span class="text-blue-600 font-medium">#$1</span>'
    )

    // メンションをハイライト
    formattedText = formattedText.replace(
      /@(\w+)/g,
      '<span class="text-blue-600 font-medium">@$1</span>'
    )

    // URLをリンク化
    formattedText = formattedText.replace(
      /(https?:\/\/[^\s]+)/g,
      '<a href="$1" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:underline">$1</a>'
    )

    return <div dangerouslySetInnerHTML={{ __html: formattedText }} />
  }, [])

  // ダウンロード済みメディアの処理
  const getMediaUrl = useCallback((media: { local_url?: string; media_id?: string }) => {
    // APIレスポンスのlocal_urlを使用（推奨）
    if (media.local_url) {
      return `${BACKEND_URL}${media.local_url}`
    }
    // フォールバック：media_idから構築
    if (media.media_id) {
      return `${BACKEND_URL}/api/tweets/media/${media.media_id}`
    }
    // 両方とも無効な場合は空文字列を返さない
    console.warn('Invalid media object:', media)
    return null
  }, [])

  // 全体の順番を保持したメディア取得（position順にソート済み）
  const allMediaSorted = useMemo(
    () =>
      tweet.downloaded_media?.slice().sort((a, b) => {
        // positionがある場合はそれで比較、なければ0として扱う
        const posA = a.position || 0
        const posB = b.position || 0
        if (posA !== posB) return posA - posB
        // 同じpositionでは添付画像を優先
        return a.order_type === 'attachment' && b.order_type === 'link' ? -1 : 1
      }) || [],
    [tweet.downloaded_media]
  )

  // 添付画像（Twitter画像）を取得
  const attachedImages = useMemo(
    () => allMediaSorted.filter(m => m.type === 'photo') || [],
    [allMediaSorted]
  )
  // リンク先画像を取得
  const linkedImages = useMemo(
    () => allMediaSorted.filter(m => m.type === 'linked_image') || [],
    [allMediaSorted]
  )

  // 表示するメディアを決定（添付画像のみ、リンク先画像は別途管理）
  const attachedVisibleMedia = useMemo(
    () => attachedImages.slice(0, isExpanded ? undefined : 4),
    [attachedImages, isExpanded]
  )
  const hasMoreAttachedMedia = attachedImages.length > 4 && !isExpanded

  // 添付画像のURLをメモ化
  const attachedMediaUrls = useMemo(
    () => attachedVisibleMedia.map(media => getMediaUrl(media) || ''),
    [attachedVisibleMedia, getMediaUrl]
  )

  // リンク画像のURLをメモ化
  const linkedMediaUrls = useMemo(
    () => linkedImages.map(media => getMediaUrl(media) || ''),
    [linkedImages, getMediaUrl]
  )

  const maxVisibleArticles = isExpanded ? undefined : 2
  const visibleArticles = useMemo(
    () => tweet.extracted_articles?.slice(0, maxVisibleArticles) || [],
    [tweet.extracted_articles, maxVisibleArticles]
  )
  const hasMoreArticles =
    tweet.extracted_articles && tweet.extracted_articles.length > (maxVisibleArticles || 0)

  return (
    <>
      <Card className={clsx('transition-all duration-200', className)}>
        <div className="p-6">
          {/* ヘッダー */}
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center space-x-3">
              {tweet.author.profile_image_url && (
                <img
                  src={tweet.author.profile_image_url}
                  alt={tweet.author.display_name}
                  className="w-12 h-12 rounded-full object-cover"
                />
              )}
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="font-semibold text-gray-900">{tweet.author.display_name}</h3>
                  <span className="text-gray-500 text-sm">@{tweet.author.username}</span>
                </div>
                <p className="text-gray-500 text-sm" title="ツイート作成時刻 (JST)">
                  {formatTweetCreatedAt(tweet.created_at)}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              {/* 画像処理ステータスバッジ */}
              {getImageProcessingBadge()}

              {/* コンテンツタイプバッジ */}
              {(attachedImages.length > 0 || linkedImages.length > 0) && (
                <Badge variant="info" size="sm">
                  <PhotoIcon className="w-3 h-3 mr-1" />
                  メディア {attachedImages.length + linkedImages.length}
                </Badge>
              )}

              {tweet.extracted_articles && tweet.extracted_articles.length > 0 && (
                <Badge variant="success" size="sm">
                  <DocumentTextIcon className="w-3 h-3 mr-1" />
                  記事 {tweet.extracted_articles.length}
                </Badge>
              )}

              <div className="relative" ref={actionsRef}>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowActions(!showActions)}
                  icon={<EllipsisHorizontalIcon className="w-4 h-4" />}
                />
                {showActions && (
                  <div className="absolute right-0 top-8 bg-white border border-gray-200 rounded-lg shadow-lg z-10 min-w-48">
                    <button
                      onClick={handleRefreshTweet}
                      className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center"
                    >
                      <ArrowPathIcon className="w-4 h-4 mr-2" />
                      このツイートを再取得
                    </button>
                    <button
                      onClick={handleDelete}
                      className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center"
                    >
                      <TrashIcon className="w-4 h-4 mr-2" />
                      このツイートを削除
                    </button>
                  </div>
                )}
              </div>

              <Button
                variant="ghost"
                size="sm"
                onClick={toggleExpanded}
                icon={
                  isExpanded ? (
                    <ChevronUpIcon className="w-4 h-4" />
                  ) : (
                    <ChevronDownIcon className="w-4 h-4" />
                  )
                }
              />
            </div>
          </div>

          {/* ツイート本文 */}
          <div
            className={clsx('text-gray-900 mb-4 leading-relaxed', !isExpanded && 'line-clamp-3')}
          >
            {renderText(tweet.text)}
          </div>

          {/* 画像処理エラー表示 */}
          {tweet.image_processing_status === 'failed' && tweet.image_processing_error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start space-x-2">
                <span className="text-red-500 text-sm">⚠️</span>
                <div className="flex-1">
                  <p className="text-red-800 text-sm font-medium">画像処理エラー</p>
                  <p className="text-red-600 text-sm mt-1">{tweet.image_processing_error}</p>
                  {tweet.image_processing_retry_count && (
                    <p className="text-red-500 text-xs mt-1">
                      リトライ回数: {tweet.image_processing_retry_count}回
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* メディア表示 */}
          {(attachedImages.length > 0 || linkedImages.length > 0) && (
            <div className="mb-4">
              {/* 添付画像（Twitter画像）*/}
              {attachedImages.length > 0 && (
                <div className="mb-3">
                  <div className="text-sm text-gray-600 mb-2 flex items-center">
                    <PhotoIcon className="w-4 h-4 mr-1" />
                    添付画像 ({attachedImages.length}件)
                  </div>
                  <div
                    className={clsx(
                      'grid gap-3 rounded-lg overflow-hidden',
                      attachedImages.length === 1
                        ? 'grid-cols-1'
                        : attachedImages.length === 2
                          ? 'grid-cols-2'
                          : 'grid-cols-2 md:grid-cols-3'
                    )}
                  >
                    {attachedVisibleMedia.map((media, index) => (
                      <div
                        key={`attached-${index}`}
                        className="relative aspect-video bg-gray-100 rounded-lg overflow-hidden cursor-pointer hover:opacity-95 transition-opacity"
                        onClick={() => {
                          const url = attachedMediaUrls[index]
                          if (url) setSelectedImage(url)
                        }}
                      >
                        {attachedMediaUrls[index] ? (
                          <img
                            src={attachedMediaUrls[index]}
                            alt=""
                            className="w-full h-full object-cover"
                            loading="lazy"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-gray-400">
                            画像読み込み失敗
                          </div>
                        )}
                        <div className="absolute bottom-1 right-1 bg-black bg-opacity-70 text-white text-xs px-1.5 py-0.5 rounded">
                          {(media.size / 1024).toFixed(0)}KB
                        </div>
                      </div>
                    ))}
                  </div>

                  {hasMoreAttachedMedia && (
                    <button
                      onClick={() => setIsExpanded(true)}
                      className="mt-2 text-sm text-blue-600 hover:text-blue-800"
                    >
                      他 {attachedImages.length - attachedVisibleMedia.length} 件の添付画像を表示
                    </button>
                  )}
                </div>
              )}

              {/* リンク先画像（折りたたみ式） */}
              {linkedImages.length > 0 && (
                <div className="mb-3">
                  <button
                    onClick={() => setShowLinkedImages(!showLinkedImages)}
                    className="w-full text-left text-sm text-gray-600 mb-2 flex items-center justify-between bg-gray-50 hover:bg-gray-100 p-3 rounded-lg transition-colors"
                  >
                    <div className="flex items-center">
                      <ArrowTopRightOnSquareIcon className="w-4 h-4 mr-1" />
                      リンク先画像 ({linkedImages.length}件)
                    </div>
                    <div className="flex items-center">
                      <span className="text-xs mr-2">{showLinkedImages ? '非表示' : '表示'}</span>
                      {showLinkedImages ? (
                        <ChevronUpIcon className="w-4 h-4" />
                      ) : (
                        <ChevronDownIcon className="w-4 h-4" />
                      )}
                    </div>
                  </button>

                  {showLinkedImages && (
                    <div
                      className={clsx(
                        'grid gap-3 rounded-lg overflow-hidden animate-in slide-in-from-top-2 duration-200',
                        linkedImages.length === 1
                          ? 'grid-cols-1'
                          : linkedImages.length === 2
                            ? 'grid-cols-2'
                            : 'grid-cols-2 md:grid-cols-3'
                      )}
                    >
                      {linkedImages.map((media, index) => (
                        <div
                          key={`linked-${index}`}
                          className="relative aspect-video bg-gray-100 rounded-lg overflow-hidden cursor-pointer hover:opacity-95 transition-opacity"
                          onClick={() => {
                            const url = linkedMediaUrls[index]
                            if (url) setSelectedImage(url)
                          }}
                        >
                          {linkedMediaUrls[index] ? (
                            <img
                              src={linkedMediaUrls[index]}
                              alt=""
                              className="w-full h-full object-cover"
                              loading="lazy"
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-gray-400">
                              画像読み込み失敗
                            </div>
                          )}
                          <div className="absolute bottom-1 right-1 bg-black bg-opacity-70 text-white text-xs px-1.5 py-0.5 rounded">
                            {(media.size / 1024).toFixed(0)}KB
                          </div>
                          <div className="absolute top-1 right-1 bg-blue-600 text-white text-xs px-1.5 py-0.5 rounded">
                            リンク
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* 記事プレビュー */}
          {visibleArticles.length > 0 && (
            <div className="mb-4 space-y-3">
              {visibleArticles.map((article, index) => (
                <div
                  key={index}
                  className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex space-x-4">
                    {article.image && (
                      <img
                        src={article.image}
                        alt=""
                        className="w-20 h-20 object-cover rounded-lg flex-shrink-0"
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium text-gray-900 text-sm line-clamp-2 mb-1">
                        {article.title}
                      </h4>
                      {article.description && (
                        <p className="text-gray-600 text-sm line-clamp-2 mb-2">
                          {article.description}
                        </p>
                      )}
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500 text-xs">
                          {article.domain || new URL(article.url).hostname}
                        </span>
                        <a
                          href={article.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-800 text-xs flex items-center"
                        >
                          読む
                          <ArrowTopRightOnSquareIcon className="w-3 h-3 ml-1" />
                        </a>
                      </div>
                    </div>
                  </div>
                </div>
              ))}

              {hasMoreArticles && (
                <button
                  onClick={() => setIsExpanded(true)}
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  他 {tweet.extracted_articles!.length - visibleArticles.length} 件の記事を表示
                </button>
              )}
            </div>
          )}

          {/* エンゲージメント統計 */}
          <div className="flex items-center justify-between pt-4 border-t border-gray-100">
            <div className="flex items-center space-x-6 text-sm text-gray-600">
              <div className="flex items-center space-x-1">
                <HeartIcon className="w-4 h-4" />
                <span>{formatNumber(tweet.public_metrics.like_count)}</span>
              </div>
              <div className="flex items-center space-x-1">
                <ArrowPathRoundedSquareIcon className="w-4 h-4" />
                <span>{formatNumber(tweet.public_metrics.retweet_count)}</span>
              </div>
              <div className="flex items-center space-x-1">
                <ChatBubbleOvalLeftIcon className="w-4 h-4" />
                <span>{formatNumber(tweet.public_metrics.reply_count)}</span>
              </div>
            </div>

            <div className="text-xs text-gray-500 text-right">
              <div>総エンゲージメント: {formatNumber(getTotalEngagement())}</div>
              {tweet.scraped_at && (
                <div className="mt-1" title="スクレイピング時刻 (JST)">
                  取得: {formatScrapedAt(tweet.scraped_at)}
                </div>
              )}
            </div>
          </div>
        </div>
      </Card>

      {/* Image Modal */}
      <ImageModal
        isOpen={selectedImage !== null}
        onClose={() => setSelectedImage(null)}
        imageUrl={selectedImage || ''}
        altText="ツイート画像"
      />
    </>
  )
}
