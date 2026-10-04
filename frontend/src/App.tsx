import { BrowserRouter, Routes, Route } from 'react-router-dom';
import AppLayout from './layouts/AppLayout';
import Landing from './pages/Landing';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import ProjectDetail from './pages/ProjectDetail';
import CreateVideo from './pages/CreateVideo';
import ScriptEditor from './pages/ScriptEditor';
import GenerateVideo from './pages/GenerateVideo';
import VideoLibrary from './pages/VideoLibrary';
import Profile from './pages/Profile';
import BatchStudio, { BatchDetail } from './pages/BatchStudio';
import NotFound from './pages/NotFound';
import { ToastProvider } from './components/ui/Toast';
import ProtectedRoute from './components/auth/ProtectedRoute';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider } from './context/AuthContext';
import AuthModal from './components/auth/AuthModal';

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ToastProvider>
        <BrowserRouter>
          <AuthModal />
          <Routes>
            {/* Landing page — no layout */}
            <Route path="/" element={<Landing />} />

            {/* App routes — guarded by ProtectedRoute */}
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <Routes>
                      <Route path="dashboard" element={<Dashboard />} />
                      <Route path="projects" element={<Projects />} />
                      <Route path="projects/:projectId" element={<ProjectDetail />} />
                      <Route path="create" element={<CreateVideo />} />
                      <Route path="scripts/:scriptId" element={<ScriptEditor />} />
                      <Route path="generate-video/:scriptId" element={<GenerateVideo />} />
                      <Route path="library" element={<VideoLibrary />} />
                      <Route path="profile" element={<Profile />} />
                      <Route path="batch" element={<BatchStudio />} />
                      <Route path="batch/:batchId" element={<BatchDetail />} />
                      <Route path="*" element={<NotFound />} />
                    </Routes>
                  </AppLayout>
                </ProtectedRoute>
              }
            />
          </Routes>
        </BrowserRouter>
        </ToastProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
