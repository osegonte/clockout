import { apiClient } from './client';

// Define types inline for now
interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    email: string;
    full_name: string | null;
    role: string;
    mode: string;
    assigned_sites: number[];
    organization_id: number;
  };
}

interface RegisterData {
  organization_name: string;
  admin_name: string;
  email: string;
  password: string;
}

interface RegisterResponse {
  message: string;
  organization_id: number;
  organization_name: string;
  admin_email: string;
  subscription_status: string;
}

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

  // Register new organization
  register: async (data: RegisterData): Promise<RegisterResponse> => {
    const response = await apiClient.post<RegisterResponse>('/auth/register/organization', data);
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
