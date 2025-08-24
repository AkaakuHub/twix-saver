import { Routes, Route, Navigate } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { Dashboard } from './components/dashboard/Dashboard'
import { UserList } from './components/users/UserList'
import { TweetList } from './components/tweets/TweetList'
import { Settings } from './components/settings/Settings'
import { ErrorBoundary } from './components/ui/ErrorBoundary'

function App() {
  return (
    <ErrorBoundary>
      <AppLayout>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/users" element={<UserList />} />
          <Route path="/tweets" element={<TweetList />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </AppLayout>
    </ErrorBoundary>
  )
}

export default App
