import { apiClient } from './client';

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

export interface CreateWorkerData {
  full_name: string;
  phone_number: string;
  id_number: string;
  site_id?: number | null;
}

export interface UpdateWorkerData {
  full_name?: string;
  phone_number?: string;
  id_number?: string;
  site_id?: number | null;
  is_active?: boolean;
}

export const workersApi = {
  getAll: async (): Promise<Worker[]> => {
    const response = await apiClient.get('/workers');
    return response.data;
  },

  getById: async (id: number): Promise<Worker> => {
    const response = await apiClient.get(`/workers/${id}`);
    return response.data;
  },

  create: async (data: CreateWorkerData): Promise<Worker> => {
    const response = await apiClient.post('/workers', data);
    return response.data;
  },

  update: async (id: number, data: UpdateWorkerData): Promise<Worker> => {
    const response = await apiClient.put(`/workers/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/workers/${id}`);
  },

  toggleStatus: async (id: number, is_active: boolean): Promise<Worker> => {
    const response = await apiClient.put(`/workers/${id}`, { is_active });
    return response.data;
  },
};
