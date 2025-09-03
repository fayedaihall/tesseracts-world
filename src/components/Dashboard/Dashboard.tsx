import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  TrendingUp, 
  Globe, 
  Zap,
  RefreshCw,
  AlertTriangle,
  CheckCircle
} from 'lucide-react';
import { StatsGrid } from './StatsGrid';
import { Analytics, HealthStatus, Job } from '../../types';
import { api } from '../../services/api';
import { useWebSocket } from '../../hooks/useWebSocket';
import { formatDistanceToNow } from 'date-fns';

export function Dashboard() {
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [recentJobs, setRecentJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { isConnected, lastMessage, jobUpdates } = useWebSocket('ws://localhost:8000/api/v1/ws');

  useEffect(() => {
    loadDashboardData();
    
    // Refresh data every 30 seconds
    const interval = setInterval(loadDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [analyticsData, healthData, jobsData] = await Promise.all([
        api.getAnalytics(),
        api.getHealthStatus(),
        api.getJobHistory(10)
      ]);

      setAnalytics(analyticsData);
      setHealthStatus(healthData);
      setRecentJobs(jobsData.jobs);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'completed':
        return 'status-badge bg-green-100 text-green-800';
      case 'in_progress':
        return 'status-badge bg-blue-100 text-blue-800';
      case 'assigned':
        return 'status-badge bg-purple-100 text-purple-800';
      case 'cancelled':
        return 'status-badge bg-red-100 text-red-800';
      case 'failed':
        return 'status-badge bg-red-100 text-red-800';
      default:
        return 'status-badge bg-yellow-100 text-yellow-800';
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">
            Real-time overview of your universal movement API
          </p>
        </div>
        
        <div className="flex items-center space-x-4">
          {/* WebSocket Status */}
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className="text-sm text-gray-600">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          
          <button
            onClick={loadDashboardData}
            disabled={loading}
            className="btn-secondary flex items-center space-x-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* System Health */}
      {healthStatus && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">System Health</h2>
            <div className={`flex items-center space-x-2 ${
              healthStatus.status === 'healthy' ? 'text-green-600' : 
              healthStatus.status === 'degraded' ? 'text-yellow-600' : 'text-red-600'
            }`}>
              {healthStatus.status === 'healthy' ? (
                <CheckCircle className="w-5 h-5" />
              ) : (
                <AlertTriangle className="w-5 h-5" />
              )}
              <span className="font-medium capitalize">{healthStatus.status}</span>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-gray-900">
                {healthStatus.healthy_providers}
              </div>
              <div className="text-sm text-gray-600">Healthy Providers</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-gray-900">
                {healthStatus.total_providers}
              </div>
              <div className="text-sm text-gray-600">Total Providers</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-gray-900">
                {Math.round((healthStatus.healthy_providers / healthStatus.total_providers) * 100)}%
              </div>
              <div className="text-sm text-gray-600">Uptime</div>
            </div>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="card border-red-200 bg-red-50">
          <div className="flex items-center space-x-2 text-red-700">
            <AlertTriangle className="w-5 h-5" />
            <span className="font-medium">Dashboard Error</span>
          </div>
          <p className="text-red-600 mt-2">{error}</p>
        </div>
      )}

      {/* Analytics Stats */}
      <StatsGrid analytics={analytics} loading={loading} />

      {/* Recent Jobs */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900">Recent Jobs</h2>
          {lastMessage && (
            <div className="text-sm text-gray-500">
              Last update: {formatDistanceToNow(new Date(), { addSuffix: true })}
            </div>
          )}
        </div>

        {recentJobs.length === 0 ? (
          <div className="text-center py-8">
            <Activity className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Recent Jobs</h3>
            <p className="text-gray-600">
              Start by creating a movement request to see job activity here
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {recentJobs.map((job) => {
              const jobUpdate = jobUpdates.get(job.id);
              const currentStatus = jobUpdate?.status || job.status;
              
              return (
                <div key={job.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                  <div className="flex items-center space-x-4">
                    <div className="p-2 bg-white rounded-lg shadow-sm">
                      {job.service_type === 'delivery' ? (
                        <Package className="w-5 h-5 text-blue-600" />
                      ) : job.service_type === 'rideshare' ? (
                        <Car className="w-5 h-5 text-green-600" />
                      ) : (
                        <Truck className="w-5 h-5 text-purple-600" />
                      )}
                    </div>
                    
                    <div>
                      <div className="flex items-center space-x-3">
                        <span className="font-medium text-gray-900">
                          {job.id.substring(0, 8)}...
                        </span>
                        <span className={getStatusBadgeClass(currentStatus)}>
                          {currentStatus.replace('_', ' ').toUpperCase()}
                        </span>
                      </div>
                      
                      <div className="flex items-center space-x-4 mt-1 text-sm text-gray-600">
                        <span className="capitalize">{job.service_type}</span>
                        <span className="capitalize">
                          {job.provider_id.replace('local_', '').replace('_', ' ')}
                        </span>
                        <span>{formatDistanceToNow(new Date(job.created_at), { addSuffix: true })}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="text-right">
                    {job.estimated_cost && (
                      <div className="font-medium text-gray-900">
                        ${job.estimated_cost.toFixed(2)}
                      </div>
                    )}
                    {job.assigned_worker && (
                      <div className="text-sm text-gray-600">
                        {job.assigned_worker.name}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Live Updates */}
      {jobUpdates.size > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Live Job Updates</h2>
          <div className="space-y-3 max-h-64 overflow-y-auto custom-scrollbar">
            {Array.from(jobUpdates.values()).reverse().map((update) => (
              <div key={`${update.job_id}-${update.timestamp}`} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-medium text-gray-900">
                      Job {update.job_id.substring(0, 8)}...
                    </span>
                    <span className={getStatusBadgeClass(update.status)}>
                      {update.status.replace('_', ' ').toUpperCase()}
                    </span>
                  </div>
                  {update.message && (
                    <p className="text-sm text-gray-600 mt-1">{update.message}</p>
                  )}
                </div>
                <div className="text-xs text-gray-500">
                  {formatDistanceToNow(new Date(update.timestamp), { addSuffix: true })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}