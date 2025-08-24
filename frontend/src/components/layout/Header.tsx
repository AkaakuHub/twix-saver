import { Bars3Icon } from '@heroicons/react/24/outline'
import { Button } from '../ui/Button'

interface HeaderProps {
  onMenuClick: () => void
}

export const Header = ({ onMenuClick }: HeaderProps) => {
  return (
    <header className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-gray-200 bg-white px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-8">
      <Button variant="ghost" size="sm" onClick={onMenuClick} className="lg:hidden">
        <Bars3Icon className="h-6 w-6" />
      </Button>

      <div className="h-6 w-px bg-gray-200 lg:hidden" />

      <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
        <div className="flex items-center gap-x-4 lg:gap-x-6">
          <h1 className="text-xl font-semibold text-gray-900">Twix Saver管理画面</h1>
        </div>

        <div className="flex items-center gap-x-4 lg:gap-x-6 ml-auto">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-sm text-gray-600">システム稼働中</span>
          </div>
        </div>
      </div>
    </header>
  )
}
