import {
  UsersIcon,
  ChatBubbleLeftRightIcon,
  CogIcon,
  CheckCircleIcon,
  ArrowUpIcon,
  ArrowDownIcon,
} from '@heroicons/react/24/outline'
import { Card } from '../ui/Card'
import { clsx } from 'clsx'

interface StatsCardProps {
  title: string
  value: number
  previousValue?: number
  icon: 'users' | 'tweets' | 'jobs' | 'success'
  color: 'blue' | 'green' | 'yellow' | 'purple' | 'red'
  suffix?: string
}

const iconMap = {
  users: UsersIcon,
  tweets: ChatBubbleLeftRightIcon,
  jobs: CogIcon,
  success: CheckCircleIcon,
}

const colorMap = {
  blue: {
    bg: 'bg-blue-500',
    text: 'text-blue-600',
    iconBg: 'bg-blue-100',
  },
  green: {
    bg: 'bg-green-500',
    text: 'text-green-600',
    iconBg: 'bg-green-100',
  },
  yellow: {
    bg: 'bg-yellow-500',
    text: 'text-yellow-600',
    iconBg: 'bg-yellow-100',
  },
  purple: {
    bg: 'bg-purple-500',
    text: 'text-purple-600',
    iconBg: 'bg-purple-100',
  },
  red: {
    bg: 'bg-red-500',
    text: 'text-red-600',
    iconBg: 'bg-red-100',
  },
}

export const StatsCard = ({
  title,
  value,
  previousValue,
  icon,
  color,
  suffix = '',
}: StatsCardProps) => {
  const Icon = iconMap[icon]
  const colors = colorMap[color]

  const formatNumber = (num: number) => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M'
    }
    if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K'
    }
    return num.toString()
  }

  const calculateChange = () => {
    if (previousValue === undefined || previousValue === 0) return null

    const change = ((value - previousValue) / previousValue) * 100
    const isPositive = change >= 0

    return {
      value: Math.abs(change),
      isPositive,
      formatted: `${Math.abs(change).toFixed(1)}%`,
    }
  }

  const change = calculateChange()

  return (
    <Card className="relative overflow-hidden">
      <div className="p-5">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <div className={clsx('p-3 rounded-lg', colors.iconBg)}>
              <Icon className={clsx('w-6 h-6', colors.text)} />
            </div>
          </div>
          <div className="ml-5 w-0 flex-1">
            <dl>
              <dt className="text-sm font-medium text-gray-500 truncate">{title}</dt>
              <dd className="flex items-baseline">
                <div className="text-2xl font-semibold text-gray-900">
                  {formatNumber(value)}
                  {suffix}
                </div>
                {change && (
                  <div className="ml-2 flex items-baseline text-sm">
                    <div
                      className={clsx(
                        'flex items-center',
                        change.isPositive ? 'text-green-600' : 'text-red-600'
                      )}
                    >
                      {change.isPositive ? (
                        <ArrowUpIcon className="w-3 h-3 mr-0.5" />
                      ) : (
                        <ArrowDownIcon className="w-3 h-3 mr-0.5" />
                      )}
                      <span className="sr-only">{change.isPositive ? '増加' : '減少'}</span>
                      {change.formatted}
                    </div>
                    <div className="ml-1 text-gray-500">前日比</div>
                  </div>
                )}
              </dd>
            </dl>
          </div>
        </div>
      </div>

      {/* 装飾的な背景要素 */}
      <div className="absolute top-0 right-0 p-3">
        <div className={clsx('w-16 h-16 rounded-full opacity-10', colors.bg)} />
      </div>
    </Card>
  )
}
