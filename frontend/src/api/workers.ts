import { apiClient } from './client';

// Worker interface - represents a worker from the API
export interface Worker {
  id: number;
  full_name: string;
  phone_number: string;
  id_number: string;
  site_id: number | null;
  site_name?: string;
  is_active: boolean;
  organization_id: number;
  created_at: string;
}

// Data required to create a new worker
export interface CreateWorkerData {
  full_name: string;
  phone_number: string;
  id_number: string;
  site_id?: number | null;
}

// Data that can be updated on a worker
export interface UpdateWorkerData {
  full_name?: string;
  phone_number?: string;
  id_number?: string;
  site_id?: number | null;
  is_active?: boolean;
}

// Workers API methods
export const workersApi = {
  // Get all workers for the current organization
  getAll: async (): Promise<Worker[]> => {
    const response = await apiClient.get('/workers');
    return response.data;
  },

  // Get a single worker by ID
  getById: async (id: number): Promise<Worker> => {
    const response = await apiClient.get(`/workers/${id}`);
    return response.data;
  },

  // Create a new worker
  create: async (data: CreateWorkerData): Promise<Worker> => {
    const response = await apiClient.post('/workers', data);
    return response.data;
  },

  // Update a worker
  update: async (id: number, data: UpdateWorkerData): Promise<Worker> => {
    const response = await apiClient.put(`/workers/${id}`, data);
    return response.data;
  },

  // Delete a worker
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/workers/${id}`);
  },

  // Toggle worker active status
  toggleStatus: async (id: number, is_active: boolean): Promise<Worker> => {
    const response = await apiClient.put(`/workers/${id}`, { is_active });
    return response.data;
  },
};
