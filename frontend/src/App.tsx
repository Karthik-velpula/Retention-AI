import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./context/AuthContext";
import AppShell from "./layouts/AppShell";
import AdminPage from "./pages/AdminPage";
import AlertsPage from "./pages/AlertsPage";
import AdvisingPage from "./pages/AdvisingPage";
import DashboardPage from "./pages/DashboardPage";
import FilterPage from "./pages/FilterPage";
import FollowUpsPage from "./pages/FollowUpsPage";
import InterventionsPage from "./pages/InterventionsPage";
import LoginPage from "./pages/LoginPage";
import StudentsPage from "./pages/StudentsPage";

function ProtectedRoutes() {
  const { role } = useAuth();

  return (
    <AppShell>
      <Routes>
        <Route path="/login" element={<Navigate to="/dashboard" replace />} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/ai-student" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/filters" element={<FilterPage />} />
        <Route path="/interventions" element={role === "faculty" ? <InterventionsPage /> : <Navigate to="/dashboard" replace />} />
        <Route path="/follow-ups" element={role === "faculty" ? <FollowUpsPage /> : <Navigate to="/dashboard" replace />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/students" element={<StudentsPage />} />
        <Route path="/admin" element={role === "admin" ? <AdminPage /> : <Navigate to="/dashboard" replace />} />
        <Route path="/advising" element={<AdvisingPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AppShell>
  );
}

function PublicRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LoginPage />} />
      <Route path="/ai-student" element={<Navigate to="/" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  const { token } = useAuth();
  return token ? <ProtectedRoutes /> : <PublicRoutes />;
}
