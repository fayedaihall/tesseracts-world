export interface Location {
  latitude: number;
  longitude: number;
  address?: string;
  city?: string;
  state?: string;
  country?: string;
  postal_code?: string;
}

export interface Vehicle {
  type: string;
  capacity_kg?: number;
  license_plate?: string;
  make?: string;
  model?: string;
}

export interface Worker {
  id: string;
  name: string;
  phone?: string;
  rating?: number;
  vehicle?: Vehicle;
  current_location?: Location;
  is_available: boolean;
  provider_id: string;
  distance_km?: number;
}

export interface Quote {
  quote_id: string;
  provider_id: string;
  service_type: ServiceType;
  estimated_cost: number;
  estimated_pickup_time: string;
  estimated_delivery_time: string;
  estimated_duration_minutes: number;
  worker_info?: Worker;
  expires_at: string;
  confidence_score: number;
}

export interface Job {
  id: string;
  service_type: ServiceType;
  status: JobStatus;
  pickup_location: Location;
  dropoff_location: Location;
  assigned_worker?: Worker;
  provider_id: string;
  estimated_cost?: number;
  actual_cost?: number;
  created_at: string;
  updated_at: string;
}

export interface JobUpdate {
  job_id: string;
  status: JobStatus;
  location?: Location;
  message?: string;
  timestamp: string;
}

export interface MovementRequest {
  service_type: ServiceType;
  pickup_location: Location;
  dropoff_location: Location;
  requested_pickup_time?: string;
  priority: Priority;
  special_requirements?: Record<string, any>;
  contact_info?: Record<string, string>;
  package_details?: Record<string, any>;
}

export interface MovementResponse {
  request_id: string;
  quotes: Quote[];
  recommended_quote_id?: string;
  created_at: string;
}

export interface Analytics {
  total_jobs: number;
  status_breakdown: Record<string, number>;
  provider_breakdown: Record<string, number>;
  service_breakdown: Record<string, number>;
  average_cost_usd: number;
  active_providers: number;
  provider_health: Record<string, boolean>;
  total_quotes_cached: number;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  providers: Record<string, boolean>;
  healthy_providers: number;
  total_providers: number;
}

export enum ServiceType {
  RIDESHARE = 'rideshare',
  DELIVERY = 'delivery',
  COURIER = 'courier',
  FREIGHT = 'freight',
  GIG_WORK = 'gig_work'
}

export enum JobStatus {
  PENDING = 'pending',
  ASSIGNED = 'assigned',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled',
  FAILED = 'failed'
}

export enum Priority {
  LOW = 'low',
  NORMAL = 'normal',
  HIGH = 'high',
  URGENT = 'urgent'
}

export interface Seller {
  id: string;
  name: string;
  website?: string;
  reputation_score: number;
  metadata: Record<string, any>;
}

export interface Product {
  id: string;
  seller_id: string;
  title: string;
  description?: string;
  price: number;
  currency: string;
  weight_kg?: number;
  categories: string[];
  images: string[];
  inventory: number;
  fulfillment_origin?: Record<string, any>;
}

export interface Order {
  id: string;
  seller_id: string;
  items: OrderItem[];
  subtotal: number;
  delivery_fee: number;
  total: number;
  status: string;
  pickup: Address;
  dropoff: Address;
  movement_job_id?: string;
  created_at: string;
}

export interface OrderItem {
  product_id: string;
  title: string;
  quantity: number;
  unit_price: number;
  currency: string;
  weight_kg?: number;
}

export interface Address {
  name?: string;
  phone?: string;
  address?: string;
  latitude: number;
  longitude: number;
}