export interface Clinic {
  id: number;
  name: string;
  code: string;
  address: string;
  phone: string;
}

export interface Me {
  id: number;
  username: string;
  full_name: string;
  roles: string[];
  active_clinic: Clinic | null;
  clinics: Clinic[];
}
