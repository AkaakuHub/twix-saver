import { useState } from 'react'
import { format } from 'date-fns'
import { ja } from 'date-fns/locale'
import {
  HeartIcon,
  ArrowPathRoundedSquareIcon,
  ChatBubbleOvalLeftIcon,
  ArrowTopRightOnSquareIcon,
  PhotoIcon,
  PlayIcon,
  DocumentTextIcon,
  ChevronDownIcon,
  ChevronUpIcon,
} from '@heroicons/react/24/outline'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
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
}

interface TweetCardProps {
  tweet: Tweet
  expanded?: boolean
  onExpand?: (tweetId: string) => void
  className?: string
}

export const TweetCard = ({
  tweet,
  expanded = false,
  onExpand,
  className = '',
}: TweetCardProps) => {
  const [isExpanded, setIsExpanded] = useState(expanded)

  const toggleExpanded = () => {
    const newExpanded = !isExpanded
    setIsExpanded(newExpanded)
    onExpand?.(tweet.id)
  }

  const formatNumber = (num: number) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
    return num.toString()
  }

  const getTotalEngagement = () => {
    const { like_count, retweet_count, reply_count, quote_count } = tweet.public_metrics
    return like_count + retweet_count + reply_count + quote_count
  }

  const renderText = (text: string) => {
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
  }

  const maxVisibleMedia = isExpanded ? undefined : 4
  const visibleMedia = tweet.media?.slice(0, maxVisibleMedia) || []
  const hasMoreMedia = tweet.media && tweet.media.length > (maxVisibleMedia || 0)

  const maxVisibleArticles = isExpanded ? undefined : 2
  const visibleArticles = tweet.extracted_articles?.slice(0, maxVisibleArticles) || []
  const hasMoreArticles =
    tweet.extracted_articles && tweet.extracted_articles.length > (maxVisibleArticles || 0)

  return (
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
              <p className="text-gray-500 text-sm">
                {format(new Date(tweet.created_at), 'MM/dd HH:mm', { locale: ja })}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {/* コンテンツタイプバッジ */}
            {tweet.media && tweet.media.length > 0 && (
              <Badge variant="info" size="sm">
                <PhotoIcon className="w-3 h-3 mr-1" />
                メディア {tweet.media.length}
              </Badge>
            )}

            {tweet.extracted_articles && tweet.extracted_articles.length > 0 && (
              <Badge variant="success" size="sm">
                <DocumentTextIcon className="w-3 h-3 mr-1" />
                記事 {tweet.extracted_articles.length}
              </Badge>
            )}

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
        <div className={clsx('text-gray-900 mb-4 leading-relaxed', !isExpanded && 'line-clamp-3')}>
          {renderText(tweet.text)}
        </div>

        {/* メディア表示 */}
        {visibleMedia.length > 0 && (
          <div className="mb-4">
            <div
              className={clsx(
                'grid gap-3 rounded-lg overflow-hidden',
                visibleMedia.length === 1
                  ? 'grid-cols-1'
                  : visibleMedia.length === 2
                    ? 'grid-cols-2'
                    : 'grid-cols-2 md:grid-cols-3'
              )}
            >
              {visibleMedia.map((media, index) => (
                <div
                  key={index}
                  className="relative aspect-video bg-gray-100 rounded-lg overflow-hidden cursor-pointer hover:opacity-95 transition-opacity"
                  onClick={() => {}}
                >
                  <img
                    src={media.preview_image_url || media.url}
                    alt=""
                    className="w-full h-full object-cover"
                  />
                  {media.type === 'video' && (
                    <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-30">
                      <PlayIcon className="w-8 h-8 text-white" />
                    </div>
                  )}
                  {media.type === 'gif' && (
                    <div className="absolute bottom-2 right-2 bg-black bg-opacity-70 text-white text-xs px-1.5 py-0.5 rounded">
                      GIF
                    </div>
                  )}
                </div>
              ))}
            </div>

            {hasMoreMedia && (
              <button
                onClick={() => setIsExpanded(true)}
                className="mt-2 text-sm text-blue-600 hover:text-blue-800"
              >
                他 {tweet.media!.length - visibleMedia.length} 件のメディアを表示
              </button>
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

          <div className="text-sm text-gray-500">
            総エンゲージメント: {formatNumber(getTotalEngagement())}
          </div>
        </div>
      </div>
    </Card>
  )
}
