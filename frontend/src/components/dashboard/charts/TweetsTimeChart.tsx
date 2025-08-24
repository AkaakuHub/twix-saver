import { useQuery } from '@tanstack/react-query'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { format } from 'date-fns'
import { ja } from 'date-fns/locale'
import { LoadingSpinner } from '../../ui/LoadingSpinner'

interface TweetTimeData {
  date: string
  count: number
}

export const TweetsTimeChart = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['tweets-time-chart'],
    queryFn: async (): Promise<TweetTimeData[]> => {
      const response = await fetch('http://localhost:8000/api/tweets/time-series?days=7')
      if (!response.ok) {
        throw new Error('ツイート時系列データの取得に失敗しました')
      }
      return response.json()
    },
    staleTime: 1000 * 60 * 5, // 5分
    refetchInterval: 1000 * 60, // 1分毎に自動更新
  })

  if (isLoading) {
    return (
      <div className="h-64 flex items-center justify-center">
        <LoadingSpinner text="チャート読み込み中..." />
      </div>
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-gray-500">データがありません</div>
    )
  }

  const formatXAxisLabel = (tickItem: string) => {
    return format(new Date(tickItem), 'MM/dd', { locale: ja })
  }

  const CustomTooltip = ({
    active,
    payload,
    label,
  }: {
    active?: boolean
    payload?: Array<{ value: number; name: string; color: string }>
    label?: string
  }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow">
          <p className="text-sm font-medium">
            {format(new Date(label || ''), 'MM月dd日', { locale: ja })}
          </p>
          <p className="text-sm text-blue-600">収集数: {payload[0].value}件</p>
        </div>
      )
    }
    return null
  }

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
          <XAxis dataKey="date" tickFormatter={formatXAxisLabel} className="text-xs" />
          <YAxis className="text-xs" />
          <Tooltip content={<CustomTooltip />} />
          <Line
            type="monotone"
            dataKey="count"
            stroke="#3B82F6"
            strokeWidth={2}
            dot={{ fill: '#3B82F6', strokeWidth: 2, r: 4 }}
            activeDot={{ r: 6, stroke: '#3B82F6', strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
