import { useState, useEffect } from 'react'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { ModalFooter } from '../ui/Modal'
import type { TargetUserResponse } from '../../types/api'

interface UserFormProps {
  user?: TargetUserResponse | null
  onSubmit: (data: UserFormData) => void
  onCancel: () => void
}

export interface UserFormData {
  username: string
  priority: number
  active: boolean
  scraping_interval_minutes: number
}

export const UserForm = ({ user, onSubmit, onCancel }: UserFormProps) => {
  const [formData, setFormData] = useState<UserFormData>({
    username: '',
    priority: 2,
    active: true,
    scraping_interval_minutes: 30,
  })

  const [errors, setErrors] = useState<Record<string, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (user) {
      setFormData({
        username: user.username,
        priority: user.priority,
        active: user.active,
        scraping_interval_minutes: user.scraping_interval_minutes || 30,
      })
    }
  }, [user])

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.username.trim()) {
      newErrors.username = 'ユーザー名は必須です'
    } else if (!/^[a-zA-Z0-9_]+$/.test(formData.username)) {
      newErrors.username = 'ユーザー名は英数字とアンダースコアのみ使用可能です'
    } else if (formData.username.length > 50) {
      newErrors.username = 'ユーザー名は50文字以内で入力してください'
    }

    if (formData.scraping_interval_minutes < 15) {
      newErrors.scraping_interval_minutes = '実行間隔は15分以上で設定してください'
    } else if (formData.scraping_interval_minutes > 1440) {
      newErrors.scraping_interval_minutes = '実行間隔は1440分（24時間）以内で設定してください'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) return

    setIsSubmitting(true)
    try {
      await onSubmit(formData)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleUsernameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/[^a-zA-Z0-9_]/g, '')
    setFormData(prev => ({ ...prev, username: value }))
    if (errors.username) {
      setErrors(prev => ({ ...prev, username: '' }))
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid grid-cols-1 gap-6">
        <Input
          label="ユーザー名"
          value={formData.username}
          onChange={handleUsernameChange}
          placeholder="Twitterのユーザー名（@なし）"
          error={errors.username}
          required
        />

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">優先度</label>
          <div className="grid grid-cols-3 gap-3">
            {[
              { value: 3, label: '高', color: 'border-red-300 bg-red-50' },
              { value: 2, label: '中', color: 'border-yellow-300 bg-yellow-50' },
              { value: 1, label: '低', color: 'border-blue-300 bg-blue-50' },
            ].map(option => (
              <label key={option.value} className="relative">
                <input
                  type="radio"
                  name="priority"
                  value={option.value}
                  checked={formData.priority === option.value}
                  onChange={e =>
                    setFormData(prev => ({
                      ...prev,
                      priority: Number(e.target.value),
                    }))
                  }
                  className="sr-only"
                />
                <div
                  className={`
                  border-2 rounded-lg p-3 text-center cursor-pointer transition-all
                  ${
                    formData.priority === option.value
                      ? `${option.color} border-opacity-100`
                      : 'border-gray-200 hover:border-gray-300'
                  }
                `}
                >
                  <span className="font-medium">{option.label}</span>
                </div>
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            実行間隔（分）
            <span className="text-red-500 ml-1">*</span>
          </label>
          <div className="space-y-3">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {[
                { value: 15, label: '15分' },
                { value: 30, label: '30分' },
                { value: 60, label: '1時間' },
                { value: 120, label: '2時間' },
              ].map(preset => (
                <button
                  key={preset.value}
                  type="button"
                  onClick={() =>
                    setFormData(prev => ({
                      ...prev,
                      scraping_interval_minutes: preset.value,
                    }))
                  }
                  className={`
                    px-3 py-2 text-sm border rounded-md transition-colors
                    ${
                      formData.scraping_interval_minutes === preset.value
                        ? 'bg-blue-50 border-blue-300 text-blue-700'
                        : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
                    }
                  `}
                >
                  {preset.label}
                </button>
              ))}
            </div>
            <Input
              label=""
              type="number"
              min={15}
              max={1440}
              value={formData.scraping_interval_minutes}
              onChange={e => {
                const value = parseInt(e.target.value) || 15
                setFormData(prev => ({
                  ...prev,
                  scraping_interval_minutes: value,
                }))
                if (errors.scraping_interval_minutes) {
                  setErrors(prev => ({ ...prev, scraping_interval_minutes: '' }))
                }
              }}
              placeholder="カスタム間隔（15-1440分）"
              error={errors.scraping_interval_minutes}
              className="max-w-xs"
            />
          </div>
          <p className="text-sm text-gray-500 mt-1">
            このアカウントをスクレイピングする間隔を設定します（最小15分）
          </p>
        </div>

        <div className="flex items-center">
          <input
            type="checkbox"
            id="active"
            checked={formData.active}
            onChange={e =>
              setFormData(prev => ({
                ...prev,
                active: e.target.checked,
              }))
            }
            className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
          />
          <label htmlFor="active" className="ml-2 block text-sm text-gray-700">
            有効にする（スクレイピングの対象とする）
          </label>
        </div>
      </div>

      <ModalFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          キャンセル
        </Button>
        <Button type="submit" loading={isSubmitting}>
          {user ? '更新' : '追加'}
        </Button>
      </ModalFooter>
    </form>
  )
}
