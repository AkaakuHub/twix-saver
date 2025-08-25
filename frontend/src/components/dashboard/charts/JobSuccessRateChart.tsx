import { useQuery } from '@tanstack/react-query'
import { useCallback } from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { LoadingSpinner } from '../../ui/LoadingSpinner'
import { API_BASE } from '../../../config/env'

export const JobSuccessRateChart = () => {
  const CustomTooltip = useCallback(
    ({
      active,
      payload,
    }: {
      active?: boolean
      payload?: Array<{ payload: { name: string; value: number; color: string } }>
    }) => {
      if (active && payload && payload.length) {
        const data = payload[0].payload
        const total = data.value
        const percentage = ((data.value / data.value) * 100).toFixed(1)

        return (
          <div className="bg-white p-3 border border-gray-200 rounded-lg shadow">
            <p className="text-sm font-medium" style={{ color: data.color }}>
              {data.name}
            </p>
            <p className="text-sm">
              {total}件 ({percentage}%)
            </p>
          </div>
        )
      }
      return null
    },
    []
  )

  const CustomLabel = useCallback(
    ({
      cx,
      cy,
      midAngle,
      innerRadius,
      outerRadius,
      percent,
    }: {
      cx?: number
      cy?: number
      midAngle?: number
      innerRadius?: number
      outerRadius?: number
      percent?: number
    }) => {
      if (!cx || !cy || midAngle === undefined || !innerRadius || !outerRadius || !percent)
        return null

      const RADIAN = Math.PI / 180
      const radius = innerRadius + (outerRadius - innerRadius) * 0.5
      const x = cx + radius * Math.cos(-midAngle * RADIAN)
      const y = cy + radius * Math.sin(-midAngle * RADIAN)

      if (percent < 0.05) return null // 5%未満は表示しない

      return (
        <text
          x={x}
          y={y}
          fill="white"
          textAnchor={x > cx ? 'start' : 'end'}
          dominantBaseline="central"
          className="text-xs font-medium"
        >
          {`${(percent * 100).toFixed(0)}%`}
        </text>
      )
    },
    []
  )

  const { data, isLoading } = useQuery({
    queryKey: ['job-success-chart'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/jobs/success-rate/`)
      if (!response.ok) {
        throw new Error('ジョブ成功率データの取得に失敗しました')
      }
      const result = await response.json()

      return [
        { name: '成功', value: result.completed_jobs || 0, color: '#10B981' },
        { name: '失敗', value: result.failed_jobs || 0, color: '#EF4444' },
      ].filter(item => item.value > 0)
    },
    staleTime: Infinity, // 手動更新のみ
    refetchOnWindowFocus: false,
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

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={CustomLabel}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: '12px' }} iconType="circle" />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
