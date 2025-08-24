import { forwardRef } from 'react'
import { clsx } from 'clsx'

interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'destructive'
}

export const Alert = forwardRef<HTMLDivElement, AlertProps>(
  ({ className, variant = 'default', ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={clsx(
          'relative w-full rounded-lg border p-4',
          variant === 'default' && 'bg-blue-50 border-blue-200 text-blue-800',
          variant === 'destructive' && 'bg-red-50 border-red-200 text-red-800',
          className
        )}
        {...props}
      />
    )
  }
)

type AlertDescriptionProps = React.HTMLAttributes<HTMLParagraphElement>

export const AlertDescription = forwardRef<HTMLParagraphElement, AlertDescriptionProps>(
  ({ className, ...props }, ref) => {
    return <div ref={ref} className={clsx('text-sm leading-relaxed', className)} {...props} />
  }
)
