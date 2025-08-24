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

interface UserFormData {
  username: string
  priority: number
  active: boolean
}

export const UserForm = ({ user, onSubmit, onCancel }: UserFormProps) => {
  const [formData, setFormData] = useState<UserFormData>({
    username: '',
    priority: 2,
    active: true,
  })

  const [errors, setErrors] = useState<Record<string, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (user) {
      setFormData({
        username: user.username,
        priority: user.priority,
        active: user.active,
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
