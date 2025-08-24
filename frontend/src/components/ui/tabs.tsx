import { createContext, useContext, useState, forwardRef } from 'react'
import { clsx } from 'clsx'

interface TabsContextValue {
  activeTab: string
  onTabChange: (value: string) => void
}

const TabsContext = createContext<TabsContextValue | undefined>(undefined)

interface TabsProps {
  defaultValue: string
  className?: string
  children: React.ReactNode
}

export function Tabs({ defaultValue, className, children }: TabsProps) {
  const [activeTab, setActiveTab] = useState(defaultValue)

  return (
    <TabsContext.Provider value={{ activeTab, onTabChange: setActiveTab }}>
      <div className={clsx('tabs', className)}>
        {children}
      </div>
    </TabsContext.Provider>
  )
}

interface TabsListProps {
  className?: string
  children: React.ReactNode
}

export function TabsList({ className, children }: TabsListProps) {
  return (
    <div className={clsx('flex space-x-1 rounded-md bg-gray-100 p-1', className)}>
      {children}
    </div>
  )
}

interface TabsTriggerProps {
  value: string
  className?: string
  children: React.ReactNode
}

export const TabsTrigger = forwardRef<HTMLButtonElement, TabsTriggerProps>(
  ({ value, className, children }, ref) => {
    const context = useContext(TabsContext)
    if (!context) throw new Error('TabsTrigger must be used within Tabs')

    const { activeTab, onTabChange } = context
    const isActive = activeTab === value

    return (
      <button
        ref={ref}
        className={clsx(
          'flex-1 px-3 py-2 text-sm font-medium rounded-sm transition-colors',
          isActive
            ? 'bg-white text-gray-900 shadow-sm'
            : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50',
          className
        )}
        onClick={() => onTabChange(value)}
      >
        {children}
      </button>
    )
  }
)

interface TabsContentProps {
  value: string
  className?: string
  children: React.ReactNode
}

export function TabsContent({ value, className, children }: TabsContentProps) {
  const context = useContext(TabsContext)
  if (!context) throw new Error('TabsContent must be used within Tabs')

  const { activeTab } = context
  
  if (activeTab !== value) return null

  return (
    <div className={clsx('mt-4', className)}>
      {children}
    </div>
  )
}