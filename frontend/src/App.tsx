import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './layouts/AppLayout';
import Landing from './pages/Landing';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import ProjectDetail from './pages/ProjectDetail';
import CreateVideo from './pages/CreateVideo';
import ScriptEditor from './pages/ScriptEditor';
import GenerateVideo from './pages/GenerateVideo';
import VideoLibrary from './pages/VideoLibrary';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider } from './context/AuthContext';
import AuthModal from './components/auth/AuthModal';

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <AuthModal />
          <Routes>
            {/* Landing page — no layout */}
            <Route path="/" element={<Landing />} />

            {/* App routes — with sidebar layout */}
            <Route
              path="/*"
              element={
                <AppLayout>
                  <Routes>
                    <Route path="dashboard" element={<Dashboard />} />
                    <Route path="projects" element={<Projects />} />
                    <Route path="projects/:projectId" element={<ProjectDetail />} />
                    <Route path="create" element={<CreateVideo />} />
                    <Route path="scripts/:scriptId" element={<ScriptEditor />} />
                    <Route path="generate-video/:scriptId" element={<GenerateVideo />} />
                    <Route path="library" element={<VideoLibrary />} />
                    <Route path="*" element={<Navigate to="/dashboard" replace />} />
                  </Routes>
                </AppLayout>
              }
            />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
