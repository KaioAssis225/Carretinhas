import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from '@/auth/ProtectedRoute'
import { AppLayout } from '@/components/layout/AppLayout'
import ChangePassword from '@/pages/ChangePassword'
import Clients from '@/pages/Clients'
import Dashboard from '@/pages/Dashboard'
import Login from '@/pages/Login'
import NotFound from '@/pages/NotFound'
import Trailers from '@/pages/Trailers'
import Rentals from '@/pages/Rentals'
import InspectionFlow from '@/pages/InspectionFlow'
import Maintenance from '@/pages/Maintenance'
import Reports from '@/pages/Reports'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/trocar-senha" element={<ChangePassword />} />
        <Route element={<AppLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/clientes" element={<Clients />} />
          <Route path="/carretas" element={<Trailers />} />
          <Route path="/locacoes" element={<Rentals />} />
          <Route path="/locacoes/:rentalId/vistoria/:type" element={<InspectionFlow />} />
          <Route path="/manutencoes" element={<Maintenance />} />
          <Route path="/financeiro" element={<Navigate to="/locacoes" replace />} />
          <Route path="/relatorios" element={<Reports />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Route>
    </Routes>
  )
}
