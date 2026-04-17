import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { useState, useEffect } from 'react';
import { fetchMe } from './api';

import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import AdminPanel from './pages/AdminPanel';

const ProtectedRoute = ({ children, requireAdmin = false }) => {
  const [auth, setAuth] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('bank_token');
    if (!token) {
      setAuth({ ok: false });
      return;
    }
    fetchMe()
      .then(res => setAuth({ ok: true, role: res.data.role }))
      .catch((err) => {
        const detail = err.response?.data?.detail || 'Session invalid';
        // Only show toast if there was actually a token (prevents toast on fresh load)
        if (token) {
          toast.error(`Security Check Failed: ${detail}`);
        }
        localStorage.removeItem('bank_token');
        setAuth({ ok: false });
      });
  }, []);

  if (auth === null) return <div className="container" style={{ padding: '50px' }}>Loading verification...</div>;

  if (!auth.ok) return <Navigate to="/login" replace />;
  if (requireAdmin && auth.role !== 'admin') return <Navigate to="/dashboard" replace />;

  return children;
};

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" />
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* User Routes */}
        <Route
          path="/dashboard/*"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />

        {/* Secure Hidden Admin Route */}
        <Route
          path="/secure-staff-access/*"
          element={
            <ProtectedRoute requireAdmin={true}>
              <AdminPanel />
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
