import { apiClient } from './client';
import { LoginResponse } from '../types/api';

export const authApi = {
  // Login with email and password
  login: async (email: string, password: string): Promise<LoginResponse> => {
    // FastAPI expects form data for OAuth2PasswordRequestForm
    const formData = new URLSearchParams();
    formData.append('username', email); // Backend expects 'username' field
    formData.append('password', password);

    const response = await apiClient.post<LoginResponse>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    return response.data;
  },

  // Get current user info
  getMe: async () => {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },

  // Logout (client-side only - just clear storage)
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  },
};