import React from 'react';
import { 
  TrendingUp, 
  Users, 
  MapPin, 
  DollarSign, 
  Clock, 
  CheckCircle,
  AlertCircle,
  XCircle
} from 'lucide-react';
import { Analytics } from '../../types';

interface StatsGridProps {
  analytics: Analytics | null;
  loading: boolean;
}

export function StatsGrid({ analytics, loading }: StatsGridProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="card animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
            <div className="h-8 bg-gray-200 rounded w-1/2"></div>
          </div>
        ))}
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="card text-center py-8">
        <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <p className="text-gray-600">Unable to load analytics data</p>
      </div>
    );
  }

  const stats = [
    {
      label: 'Total Jobs',
      value: analytics.total_jobs.toLocaleString(),
      icon: MapPin,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
    },
    {
      label: 'Active Providers',
      value: `${analytics.active_providers}`,
      icon: Users,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
    },
    {
      label: 'Average Cost',
      value: `$${analytics.average_cost_usd.toFixed(2)}`,
      icon: DollarSign,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
    },
    {
      label: 'Cached Quotes',
      value: analytics.total_quotes_cached.toLocaleString(),
      icon: Clock,
      color: 'text-orange-600',
      bgColor: 'bg-orange-100',
    },
  ];

  const statusStats = [
    {
      label: 'Completed',
      value: analytics.status_breakdown.completed || 0,
      icon: CheckCircle,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
    },
    {
      label: 'In Progress',
      value: analytics.status_breakdown.in_progress || 0,
      icon: TrendingUp,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
    },
    {
      label: 'Pending',
      value: analytics.status_breakdown.pending || 0,
      icon: Clock,
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-100',
    },
    {
      label: 'Cancelled',
      value: analytics.status_breakdown.cancelled || 0,
      icon: XCircle,
      color: 'text-red-600',
      bgColor: 'bg-red-100',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Main Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="card hover:shadow-md transition-shadow duration-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">{stat.label}</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">{stat.value}</p>
                </div>
                <div className={`p-3 rounded-lg ${stat.bgColor}`}>
                  <Icon className={`w-6 h-6 ${stat.color}`} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Status Breakdown */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Job Status Breakdown</h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {statusStats.map((stat) => {
            const Icon = stat.icon;
            return (
              <div key={stat.label} className="flex items-center space-x-3 p-3 rounded-lg bg-gray-50">
                <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                  <Icon className={`w-4 h-4 ${stat.color}`} />
                </div>
                <div>
                  <p className="text-sm text-gray-600">{stat.label}</p>
                  <p className="text-lg font-semibold text-gray-900">{stat.value}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Provider Health */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Provider Health Status</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(analytics.provider_health).map(([provider, isHealthy]) => (
            <div key={provider} className="flex items-center justify-between p-3 rounded-lg bg-gray-50">
              <span className="font-medium text-gray-900 capitalize">
                {provider.replace('local_', '').replace('_', ' ')}
              </span>
              <div className={`flex items-center space-x-2 ${isHealthy ? 'text-green-600' : 'text-red-600'}`}>
                <div className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span className="text-sm font-medium">{isHealthy ? 'Healthy' : 'Unhealthy'}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}