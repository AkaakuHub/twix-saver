import { Fragment } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import { Button } from './Button'

interface ErrorModalProps {
  isOpen: boolean
  onClose?: () => void
  title: string
  message: string
  showCloseButton?: boolean
  onRetry?: () => void
}

export const ErrorModal = ({
  isOpen,
  onClose,
  title,
  message,
  showCloseButton = false,
  onRetry,
}: ErrorModalProps) => {
  const handleClose = () => {
    if (onClose && showCloseButton) {
      onClose()
    }
  }

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={handleClose} static={!showCloseButton}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-slate-500/20 backdrop-blur-sm" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-8 text-left align-middle shadow-xl transition-all border border-slate-200">
                <div className="flex flex-col items-center text-center">
                  <div className="flex items-center justify-center w-16 h-16 rounded-full bg-amber-50 mb-6">
                    <ExclamationTriangleIcon className="w-8 h-8 text-amber-500" />
                  </div>

                  <Dialog.Title as="h3" className="text-xl font-semibold text-slate-800 mb-3">
                    {title}
                  </Dialog.Title>

                  <p className="text-slate-600 leading-relaxed mb-8">{message}</p>

                  <div className="flex gap-3 w-full justify-center">
                    {onRetry && (
                      <Button
                        onClick={onRetry}
                        className="bg-amber-500 hover:bg-amber-600 text-white px-6 py-2 rounded-lg transition-colors"
                      >
                        再試行
                      </Button>
                    )}
                    {showCloseButton && onClose && (
                      <Button
                        variant="outline"
                        onClick={onClose}
                        className="border-slate-300 text-slate-700 hover:bg-slate-50 px-6 py-2 rounded-lg transition-colors"
                      >
                        閉じる
                      </Button>
                    )}
                  </div>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}
