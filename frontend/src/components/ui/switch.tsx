import { forwardRef } from 'react'
import { clsx } from 'clsx'

interface SwitchProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string
  description?: string
  onCheckedChange?: (checked: boolean) => void
}

export const Switch = forwardRef<HTMLInputElement, SwitchProps>(
  ({ className, label, description, checked, onCheckedChange, onChange, ...props }, ref) => {
    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const newChecked = e.target.checked
      onCheckedChange?.(newChecked)
      onChange?.(e)
    }


    return (
      <div className="flex items-center space-x-3">
        <label className="relative inline-flex cursor-pointer">
          <input
            type="checkbox"
            className="sr-only"
            ref={ref}
            checked={checked}
            onChange={handleChange}
            {...props}
          />
          <div
            className={clsx(
              'block w-10 h-6 rounded-full transition-colors duration-200 ease-in-out',
              checked ? 'bg-blue-600' : 'bg-gray-300',
              className
            )}
          >
            <div
              className={clsx(
                'absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform duration-200 ease-in-out shadow-sm',
                checked ? 'transform translate-x-4' : 'transform translate-x-0'
              )}
            />
          </div>
        </label>
        {(label || description) && (
          <div className="flex-1">
            {label && <div className="text-sm font-medium text-gray-700">{label}</div>}
            {description && <div className="text-sm text-gray-500">{description}</div>}
          </div>
        )}
      </div>
    )
  }
)