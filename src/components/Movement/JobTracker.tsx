import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import { 
  Clock, 
  MapPin, 
  User, 
  Phone, 
  Star, 
  Package,
  CheckCircle,
  XCircle,
  AlertCircle,
  Navigation
} from 'lucide-react';
import { Job, JobUpdate, Location } from '../../types';
import { api } from '../../services/api';
import { formatDistanceToNow } from 'date-fns';
import 'leaflet/dist/leaflet.css';

// Fix for default markers in react-leaflet
import L from 'leaflet';
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.divIcon({
  html: `<div class="w-6 h-6 bg-primary-600 rounded-full border-2 border-white shadow-lg"></div>`,
  className: 'custom-div-icon',
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

L.Marker.prototype.options.icon = DefaultIcon;

interface JobTrackerProps {
  job: Job;
  onClose: () => void;
}

export function JobTracker({ job, onClose }: JobTrackerProps) {
  const [jobUpdate, setJobUpdate] = useState<JobUpdate | null>(null);
  const [workerLocation, setWorkerLocation] = useState<Location | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchJobData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Get job status
        const status = await api.getJobStatus(job.id);
        setJobUpdate(status);

        // Get worker location if job is in progress
        if (status.status === 'in_progress' || status.status === 'assigned') {
          try {
            const trackData = await api.trackJob(job.id);
            if (trackData.location) {
              setWorkerLocation(trackData.location);
            }
          } catch (trackError) {
            console.warn('Could not get worker location:', trackError);
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch job data');
      } finally {
        setLoading(false);
      }
    };

    fetchJobData();

    // Poll for updates every 10 seconds
    const interval = setInterval(fetchJobData, 10000);

    return () => clearInterval(interval);
  }, [job.id]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'cancelled':
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-600" />;
      case 'in_progress':
        return <Navigation className="w-5 h-5 text-blue-600" />;
      case 'assigned':
        return <User className="w-5 h-5 text-purple-600" />;
      default:
        return <Clock className="w-5 h-5 text-yellow-600" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-700 bg-green-100';
      case 'cancelled':
      case 'failed':
        return 'text-red-700 bg-red-100';
      case 'in_progress':
        return 'text-blue-700 bg-blue-100';
      case 'assigned':
        return 'text-purple-700 bg-purple-100';
      default:
        return 'text-yellow-700 bg-yellow-100';
    }
  };

  if (loading) {
    return (
      <div className="card">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="flex items-center space-x-2 text-red-600 mb-4">
          <AlertCircle className="w-5 h-5" />
          <span className="font-medium">Error loading job data</span>
        </div>
        <p className="text-gray-600 mb-4">{error}</p>
        <button onClick={onClose} className="btn-secondary">
          Close
        </button>
      </div>
    );
  }

  // Calculate map bounds
  const locations = [job.pickup_location, job.dropoff_location];
  if (workerLocation) {
    locations.push(workerLocation);
  }

  const bounds = locations.map(loc => [loc.latitude, loc.longitude] as [number, number]);
  const center = bounds.reduce(
    (acc, coord) => [acc[0] + coord[0] / bounds.length, acc[1] + coord[1] / bounds.length],
    [0, 0]
  ) as [number, number];

  return (
    <div className="space-y-6">
      {/* Job Header */}
      <div className="card">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Job Tracking</h2>
            <p className="text-gray-600">Job ID: {job.id}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <XCircle className="w-6 h-6" />
          </button>
        </div>

        {/* Status */}
        {jobUpdate && (
          <div className="flex items-center space-x-3 mb-4">
            {getStatusIcon(jobUpdate.status)}
            <div>
              <span className={`status-badge ${getStatusColor(jobUpdate.status)}`}>
                {jobUpdate.status.replace('_', ' ').toUpperCase()}
              </span>
              {jobUpdate.message && (
                <p className="text-sm text-gray-600 mt-1">{jobUpdate.message}</p>
              )}
            </div>
          </div>
        )}

        {/* Provider and Worker Info */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Provider</h4>
            <p className="text-gray-600 capitalize">
              {job.provider_id.replace('local_', '').replace('_', ' ')}
            </p>
          </div>
          
          {job.assigned_worker && (
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Assigned Worker</h4>
              <div className="flex items-center space-x-2">
                <User className="w-4 h-4 text-gray-400" />
                <span className="text-gray-900">{job.assigned_worker.name}</span>
                {job.assigned_worker.rating && (
                  <div className="flex items-center space-x-1">
                    <Star className="w-3 h-3 text-yellow-500 fill-current" />
                    <span className="text-sm text-gray-600">{job.assigned_worker.rating}</span>
                  </div>
                )}
              </div>
              {job.assigned_worker.phone && (
                <div className="flex items-center space-x-2 mt-1">
                  <Phone className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-600">{job.assigned_worker.phone}</span>
                </div>
              )}
              {job.assigned_worker.vehicle && (
                <div className="flex items-center space-x-2 mt-1">
                  <VehicleIcon className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-600 capitalize">
                    {job.assigned_worker.vehicle.type}
                    {job.assigned_worker.vehicle.license_plate && 
                      ` • ${job.assigned_worker.vehicle.license_plate}`
                    }
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Map */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Live Tracking</h3>
        <div className="h-96 rounded-lg overflow-hidden">
          <MapContainer
            center={center}
            zoom={13}
            style={{ height: '100%', width: '100%' }}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            
            {/* Pickup Location */}
            <Marker position={[job.pickup_location.latitude, job.pickup_location.longitude]}>
              <Popup>
                <div className="text-center">
                  <div className="font-medium text-green-700">Pickup Location</div>
                  {job.pickup_location.address && (
                    <div className="text-sm text-gray-600 mt-1">{job.pickup_location.address}</div>
                  )}
                </div>
              </Popup>
            </Marker>

            {/* Dropoff Location */}
            <Marker position={[job.dropoff_location.latitude, job.dropoff_location.longitude]}>
              <Popup>
                <div className="text-center">
                  <div className="font-medium text-blue-700">Dropoff Location</div>
                  {job.dropoff_location.address && (
                    <div className="text-sm text-gray-600 mt-1">{job.dropoff_location.address}</div>
                  )}
                </div>
              </Popup>
            </Marker>

            {/* Worker Location */}
            {workerLocation && (
              <Marker position={[workerLocation.latitude, workerLocation.longitude]}>
                <Popup>
                  <div className="text-center">
                    <div className="font-medium text-purple-700">
                      {job.assigned_worker?.name || 'Worker'} Location
                    </div>
                    <div className="text-sm text-gray-600 mt-1">
                      Last updated: {formatDistanceToNow(new Date(), { addSuffix: true })}
                    </div>
                  </div>
                </Popup>
              </Marker>
            )}

            {/* Route Line */}
            <Polyline
              positions={[
                [job.pickup_location.latitude, job.pickup_location.longitude],
                [job.dropoff_location.latitude, job.dropoff_location.longitude]
              ]}
              color="#3b82f6"
              weight={3}
              opacity={0.7}
            />
          </MapContainer>
        </div>
      </div>

      {/* Job Details */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Job Details</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Pickup Details */}
          <div>
            <h4 className="font-medium text-gray-900 mb-3 flex items-center space-x-2">
              <MapPin className="w-4 h-4 text-green-600" />
              <span>Pickup</span>
            </h4>
            <div className="space-y-2 text-sm">
              <p className="text-gray-600">
                {job.pickup_location.address || 
                 `${job.pickup_location.latitude.toFixed(4)}, ${job.pickup_location.longitude.toFixed(4)}`}
              </p>
              {job.requested_pickup_time && (
                <p className="text-gray-500">
                  Requested: {formatDistanceToNow(new Date(job.requested_pickup_time), { addSuffix: true })}
                </p>
              )}
              {job.actual_pickup_time && (
                <p className="text-green-600 font-medium">
                  Picked up: {formatDistanceToNow(new Date(job.actual_pickup_time), { addSuffix: true })}
                </p>
              )}
            </div>
          </div>

          {/* Dropoff Details */}
          <div>
            <h4 className="font-medium text-gray-900 mb-3 flex items-center space-x-2">
              <MapPin className="w-4 h-4 text-blue-600" />
              <span>Dropoff</span>
            </h4>
            <div className="space-y-2 text-sm">
              <p className="text-gray-600">
                {job.dropoff_location.address || 
                 `${job.dropoff_location.latitude.toFixed(4)}, ${job.dropoff_location.longitude.toFixed(4)}`}
              </p>
              {job.estimated_delivery_time && (
                <p className="text-gray-500">
                  Estimated: {formatDistanceToNow(new Date(job.estimated_delivery_time), { addSuffix: true })}
                </p>
              )}
              {job.actual_delivery_time && (
                <p className="text-green-600 font-medium">
                  Delivered: {formatDistanceToNow(new Date(job.actual_delivery_time), { addSuffix: true })}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Package Details */}
        {(job.package_weight_kg || job.fragile || job.description) && (
          <div className="mt-6 pt-6 border-t border-gray-100">
            <h4 className="font-medium text-gray-900 mb-3 flex items-center space-x-2">
              <Package className="w-4 h-4 text-gray-600" />
              <span>Package Details</span>
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              {job.package_weight_kg && (
                <div>
                  <span className="text-gray-500">Weight:</span>
                  <span className="ml-2 text-gray-900">{job.package_weight_kg}kg</span>
                </div>
              )}
              {job.fragile && (
                <div>
                  <span className="text-gray-500">Special:</span>
                  <span className="ml-2 text-orange-600 font-medium">Fragile</span>
                </div>
              )}
              {job.package_value && (
                <div>
                  <span className="text-gray-500">Value:</span>
                  <span className="ml-2 text-gray-900">${job.package_value}</span>
                </div>
              )}
            </div>
            {job.description && (
              <div className="mt-3">
                <span className="text-gray-500">Description:</span>
                <p className="text-gray-900 mt-1">{job.description}</p>
              </div>
            )}
          </div>
        )}

        {/* Cost Information */}
        <div className="mt-6 pt-6 border-t border-gray-100">
          <h4 className="font-medium text-gray-900 mb-3">Cost Information</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            {job.estimated_cost && (
              <div>
                <span className="text-gray-500">Estimated Cost:</span>
                <span className="ml-2 text-gray-900">${job.estimated_cost}</span>
              </div>
            )}
            {job.actual_cost && (
              <div>
                <span className="text-gray-500">Actual Cost:</span>
                <span className="ml-2 text-green-600 font-medium">${job.actual_cost}</span>
              </div>
            )}
          </div>
        </div>

        {/* Timestamps */}
        <div className="mt-6 pt-6 border-t border-gray-100">
          <h4 className="font-medium text-gray-900 mb-3">Timeline</h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Created:</span>
              <span className="text-gray-900">
                {formatDistanceToNow(new Date(job.created_at), { addSuffix: true })}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Last Updated:</span>
              <span className="text-gray-900">
                {formatDistanceToNow(new Date(job.updated_at), { addSuffix: true })}
              </span>
            </div>
            {jobUpdate && (
              <div className="flex justify-between">
                <span className="text-gray-500">Status Updated:</span>
                <span className="text-gray-900">
                  {formatDistanceToNow(new Date(jobUpdate.timestamp), { addSuffix: true })}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}