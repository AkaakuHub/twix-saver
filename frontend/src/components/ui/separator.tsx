import { forwardRef } from 'react'
import { clsx } from 'clsx'

interface SeparatorProps extends React.HTMLAttributes<HTMLDivElement> {
  orientation?: 'horizontal' | 'vertical'
}

export const Separator = forwardRef<HTMLDivElement, SeparatorProps>(
  ({ className, orientation = 'horizontal', ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={clsx(
          'bg-gray-200',
          orientation === 'horizontal' ? 'h-px w-full' : 'w-px h-full',
          className
        )}
        {...props}
      />
    )
  }
)
