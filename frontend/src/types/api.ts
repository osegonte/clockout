// API Response Types
export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
  mode: string;
  assigned_sites: number[];
  organization_id: number;
}