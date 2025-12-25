import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import DashboardLayout from './components/DashboardLayout';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Workers from './pages/Workers';
import Sites from './pages/Sites';
import Attendance from './pages/Attendance';
import Managers from './pages/Managers';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          
          {/* Protected Routes with Dashboard Layout */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <Dashboard />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          
          <Route
            path="/workers"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <Workers />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          
          <Route
            path="/sites"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <Sites />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          
          <Route
            path="/attendance"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <Attendance />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          
          <Route
            path="/managers"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <Managers />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          
          {/* Default Route - Redirect to dashboard */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          
          {/* 404 - Redirect to dashboard */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;