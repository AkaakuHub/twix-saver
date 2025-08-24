import { clsx } from 'clsx'

interface CardProps {
  children: React.ReactNode
  className?: string
  padding?: 'none' | 'sm' | 'md' | 'lg'
  shadow?: 'none' | 'sm' | 'md' | 'lg'
}

export const Card = ({ children, className, padding = 'md', shadow = 'md' }: CardProps) => {
  const paddingClasses = {
    none: '',
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-6',
  }

  const shadowClasses = {
    none: '',
    sm: 'shadow-sm',
    md: 'shadow',
    lg: 'shadow-lg',
  }

  return (
    <div
      className={clsx(
        'bg-white rounded-lg border border-gray-200',
        paddingClasses[padding],
        shadowClasses[shadow],
        className
      )}
    >
      {children}
    </div>
  )
}

interface CardHeaderProps {
  children: React.ReactNode
  className?: string
}

export const CardHeader = ({ children, className }: CardHeaderProps) => (
  <div className={clsx('mb-4', className)}>{children}</div>
)

interface CardTitleProps {
  children: React.ReactNode
  className?: string
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6'
}

export const CardTitle = ({ children, className, as: Component = 'h3' }: CardTitleProps) => (
  <Component className={clsx('text-lg font-semibold text-gray-900', className)}>
    {children}
  </Component>
)

interface CardContentProps {
  children: React.ReactNode
  className?: string
}

export const CardContent = ({ children, className }: CardContentProps) => (
  <div className={className}>{children}</div>
)

interface CardDescriptionProps {
  children: React.ReactNode
  className?: string
}

export const CardDescription = ({ children, className }: CardDescriptionProps) => (
  <p className={clsx('text-sm text-gray-600 mt-1', className)}>{children}</p>
)
