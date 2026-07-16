import { apiFetch } from '@/api/client'
import type { PageMeta } from '@/api/clients'

export type MaintenanceStatus = 'OPEN' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED'
export type MaintenancePriority = 'LOW' | 'MEDIUM' | 'HIGH'
export interface MaintenanceData { id: string; trailer_id: string; type: string; description: string; priority: MaintenancePriority; starts_at: string; expected_end_at: string | null; completed_at: string | null; estimated_cost: string | null; final_cost: string | null; status: MaintenanceStatus; assigned_to_user_id: string | null }
export interface MaintenancePayload { trailer_id: string; type: string; description: string; priority: MaintenancePriority; starts_at: string; expected_end_at?: string | null; estimated_cost?: number | null }
export interface OperationalAlerts { overdue_rentals: number; returns_next_24h: number; open_maintenance: number; high_priority_maintenance: number }
export function listMaintenance(): Promise<{ data: MaintenanceData[]; meta: PageMeta }> { return apiFetch('/maintenance-orders?page=1&page_size=100') }
export function createMaintenance(payload: MaintenancePayload): Promise<MaintenanceData> { return apiFetch('/maintenance-orders', { method: 'POST', body: JSON.stringify(payload) }) }
export function startMaintenance(id: string): Promise<MaintenanceData> { return apiFetch(`/maintenance-orders/${id}/start`, { method: 'POST' }) }
export function completeMaintenance(id: string, finalCost: number): Promise<MaintenanceData> { return apiFetch(`/maintenance-orders/${id}/complete`, { method: 'POST', body: JSON.stringify({ final_cost: finalCost }) }) }
export function cancelMaintenance(id: string): Promise<MaintenanceData> { return apiFetch(`/maintenance-orders/${id}/cancel`, { method: 'POST' }) }
export function getOperationalAlerts(): Promise<OperationalAlerts> { return apiFetch('/operational/alerts') }
