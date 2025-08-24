import { RetryButton } from './RetryButton'

interface EmptyStateWithRetryProps {
  title: string
  message: string
  onRetry?: () => void
  isLoading?: boolean
  showRetry?: boolean
  icon?: React.ReactNode
}

export const EmptyStateWithRetry = ({
  title,
  message,
  onRetry,
  isLoading = false,
  showRetry = true,
  icon,
}: EmptyStateWithRetryProps) => {
  const defaultIcon = (
    <svg className="h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  )

  return (
    <div className="text-center py-12">
      <div className="mx-auto flex items-center justify-center h-12 w-12 mb-4">
        {icon || defaultIcon}
      </div>
      <h3 className="text-lg font-medium text-gray-900 mb-2">{title}</h3>
      <p className="text-sm text-gray-500 mb-6 max-w-sm mx-auto">{message}</p>
      {showRetry && onRetry && <RetryButton onRetry={onRetry} isLoading={isLoading} />}
    </div>
  )
}
