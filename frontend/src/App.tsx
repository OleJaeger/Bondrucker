import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { ToastProvider } from './context/ToastContext'
import { Layout } from './components/Layout'
import { CreateJob } from './pages/CreateJob'
import { Dashboard } from './pages/Dashboard'
import { FailedJobs } from './pages/FailedJobs'
import { Presets } from './pages/Presets'
import { PrinterStatus } from './pages/PrinterStatus'
import { Queue } from './pages/Queue'
import { Settings } from './pages/Settings'

export default function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="jobs/new" element={<CreateJob />} />
            <Route path="presets" element={<Presets />} />
            <Route path="queue" element={<Queue />} />
            <Route path="failed" element={<FailedJobs />} />
            <Route path="printer" element={<PrinterStatus />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  )
}
