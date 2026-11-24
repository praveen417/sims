import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./AuthContext";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Inventory from "./pages/Inventory";
import ImportAssets from "./pages/ImportAssets";
import ExportData from "./pages/ExportData";
import AuditLogs from "./pages/AuditLogs";
import Reports from "./pages/Reports";
import Users from "./pages/Users";
import Settings from "./pages/Settings";
import ChangeRequests from "./pages/ChangeRequests";

function Guard({ perm, children }) {
  const { user, can } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (perm && !can(perm)) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  const { user } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      <Route element={<Guard><Layout /></Guard>}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/inventory" element={<Inventory />} />
        <Route path="/import" element={<Guard perm="asset:import"><ImportAssets /></Guard>} />
        <Route path="/changes" element={<Guard perm="change:view"><ChangeRequests /></Guard>} />
        <Route path="/export" element={<Guard perm="asset:export"><ExportData /></Guard>} />
        <Route path="/reports" element={<Guard perm="report:view"><Reports /></Guard>} />
        <Route path="/audit" element={<Guard perm="audit:view"><AuditLogs /></Guard>} />
        <Route path="/users" element={<Guard perm="user:manage"><Users /></Guard>} />
        <Route path="/settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
