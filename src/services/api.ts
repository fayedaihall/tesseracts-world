import { 
  MovementRequest, 
  MovementResponse, 
  Job, 
  JobUpdate, 
  Analytics, 
  HealthStatus, 
  Worker,
  ServiceType,
  Seller,
  Product,
  Order
} from '../types';

const API_BASE_URL = 'http://localhost:8000/api/v1';
const API_KEY = 'tesseracts_demo_key_12345';

class TesseractsAPI {
  private baseURL: string;
  private apiKey: string;

  constructor(baseURL: string = API_BASE_URL, apiKey: string = API_KEY) {
    this.baseURL = baseURL;
    this.apiKey = apiKey;
  }

  private getHeaders(): HeadersInit {
    return {
      'Authorization': `Bearer ${this.apiKey}`,
      'Content-Type': 'application/json',
    };
  }

  private async request<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        ...this.getHeaders(),
        ...options.headers,
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Error: ${response.status} - ${errorText}`);
    }

    return response.json();
  }

  // Movement API
  async requestMovement(request: MovementRequest): Promise<MovementResponse> {
    return this.request<MovementResponse>('/movement/request', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async acceptQuote(quoteId: string, request: MovementRequest): Promise<Job> {
    return this.request<Job>(`/movement/accept?quote_id=${quoteId}`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getJobStatus(jobId: string): Promise<JobUpdate> {
    return this.request<JobUpdate>(`/jobs/${jobId}/status`);
  }

  async trackJob(jobId: string): Promise<{ job_id: string; location?: any }> {
    return this.request(`/jobs/${jobId}/track`);
  }

  async cancelJob(jobId: string): Promise<{ success: boolean; message: string }> {
    return this.request(`/jobs/${jobId}`, {
      method: 'DELETE',
    });
  }

  async getAvailableWorkers(
    latitude: number,
    longitude: number,
    serviceType: ServiceType,
    radiusKm: number = 10
  ): Promise<{ workers: Worker[]; count: number }> {
    const params = new URLSearchParams({
      latitude: latitude.toString(),
      longitude: longitude.toString(),
      service_type: serviceType,
      radius_km: radiusKm.toString(),
    });

    return this.request(`/workers?${params}`);
  }

  async getJobHistory(limit: number = 50): Promise<{ jobs: Job[]; count: number }> {
    return this.request(`/jobs?limit=${limit}`);
  }

  async getAnalytics(): Promise<Analytics> {
    return this.request<Analytics>('/analytics');
  }

  async getHealthStatus(): Promise<HealthStatus> {
    return this.request<HealthStatus>('/health');
  }

  // Commerce API
  async getSellers(): Promise<{ sellers: Seller[]; count: number }> {
    return this.request('/sellers');
  }

  async getProducts(sellerId?: string): Promise<{ products: Product[]; count: number }> {
    const params = sellerId ? `?seller_id=${sellerId}` : '';
    return this.request(`/products${params}`);
  }

  async searchProducts(query: string): Promise<{ products: Product[]; count: number }> {
    const params = new URLSearchParams({ q: query });
    return this.request(`/products/search?${params}`);
  }

  async createOrder(orderData: any): Promise<{ order: Order; delivery_quotes: MovementResponse }> {
    return this.request('/orders', {
      method: 'POST',
      body: JSON.stringify(orderData),
    });
  }

  async getOrder(orderId: string): Promise<Order> {
    return this.request(`/orders/${orderId}`);
  }

  async fundOrderEscrow(orderId: string): Promise<any> {
    return this.request(`/orders/${orderId}/fund`, {
      method: 'POST',
    });
  }

  async acceptOrderDelivery(orderId: string, quoteId: string): Promise<any> {
    return this.request(`/orders/${orderId}/accept?quote_id=${quoteId}`, {
      method: 'POST',
    });
  }
}

export const api = new TesseractsAPI();