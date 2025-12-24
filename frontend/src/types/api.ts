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

export interface Worker {
  id: number;
  name: string;
  phone: string | null;
  employee_id: string | null;
  organization_id: number;
  site_id: number | null;
  is_active: boolean;
}

export interface Site {
  id: number;
  name: string;
  organization_id: number;
  gps_lat: number;
  gps_lon: number;
  radius_m: number;
}

export interface DailySummary {
  date: string;
  site_name: string | null;
  total_workers: number;
  present: number;
  absent: number;
  late: number;
  on_time: number;
  total_hours_worked: number;
  workers_present: WorkerAttendanceStatus[];
  workers_absent: { worker_id: number; name: string }[];
}

export interface WorkerAttendanceStatus {
  worker_id: number;
  name: string;
  check_in_time: string | null;
  check_out_time: string | null;
  hours_worked: number | null;
  status: string; // "on_time", "late", "absent", "present"
}

export interface WorkerOnSite {
  worker_id: number;
  name: string;
  site_name: string;
  checked_in_at: string;
  hours_on_site: number;
}

export interface WorkerStatusResponse {
  timestamp: string;
  on_site_now: WorkerOnSite[];
  checked_out: { worker_id: number; name: string; checked_out_at: string }[];
  not_yet_arrived: { worker_id: number; name: string }[];
}