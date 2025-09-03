import React, { useState, useEffect } from 'react';
import { 
  MapPin, 
  Search, 
  Clock, 
  Zap, 
  Package, 
  Car,
  Bike,
  Truck,
  Users,
  ArrowRight,
  RefreshCw
} from 'lucide-react';
import { LocationPicker } from './LocationPicker';
import { QuoteCard } from './QuoteCard';
import { JobTracker } from './JobTracker';
import { 
  Location, 
  MovementRequest, 
  Quote, 
  Job, 
  ServiceType, 
  Priority,
  Worker 
} from '../../types';
import { api } from '../../services/api';

export function MovementDemo() {
  const [pickupLocation, setPickupLocation] = useState<Location | null>(null);
  const [dropoffLocation, setDropoffLocation] = useState<Location | null>(null);
  const [serviceType, setServiceType] = useState<ServiceType>(ServiceType.DELIVERY);
  const [priority, setPriority] = useState<Priority>(Priority.NORMAL);
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [selectedQuote, setSelectedQuote] = useState<Quote | null>(null);
  const [currentJob, setCurrentJob] = useState<Job | null>(null);
  const [availableWorkers, setAvailableWorkers] = useState<Worker[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const serviceTypeOptions = [
    { value: ServiceType.DELIVERY, label: 'Delivery', icon: Package, description: 'Package & food delivery' },
    { value: ServiceType.RIDESHARE, label: 'Rideshare', icon: Car, description: 'Personal transportation' },
    { value: ServiceType.COURIER, label: 'Courier', icon: Bike, description: 'Express courier service' },
    { value: ServiceType.FREIGHT, label: 'Freight', icon: Truck, description: 'Large cargo transport' },
  ];

  const priorityOptions = [
    { value: Priority.LOW, label: 'Low', color: 'text-gray-600', description: 'Cost-optimized' },
    { value: Priority.NORMAL, label: 'Normal', color: 'text-blue-600', description: 'Balanced' },
    { value: Priority.HIGH, label: 'High', color: 'text-orange-600', description: 'Time-optimized' },
    { value: Priority.URGENT, label: 'Urgent', color: 'text-red-600', description: 'Fastest available' },
  ];

  const handleRequestQuotes = async () => {
    if (!pickupLocation || !dropoffLocation) {
      setError('Please select both pickup and dropoff locations');
      return;
    }

    setLoading(true);
    setError(null);
    setQuotes([]);
    setSelectedQuote(null);

    try {
      const request: MovementRequest = {
        service_type: serviceType,
        pickup_location: pickupLocation,
        dropoff_location: dropoffLocation,
        priority,
        package_details: serviceType === ServiceType.DELIVERY ? {
          weight_kg: 2.5,
          fragile: false
        } : undefined,
        special_requirements: serviceType === ServiceType.RIDESHARE ? {
          passenger_count: 1
        } : undefined
      };

      const response = await api.requestMovement(request);
      setQuotes(response.quotes);

      // Also fetch available workers
      const workersResponse = await api.getAvailableWorkers(
        pickupLocation.latitude,
        pickupLocation.longitude,
        serviceType,
        15
      );
      setAvailableWorkers(workersResponse.workers);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get quotes');
    } finally {
      setLoading(false);
    }
  };

  const handleAcceptQuote = async (quote: Quote) => {
    if (!pickupLocation || !dropoffLocation) return;

    setLoading(true);
    setError(null);

    try {
      const request: MovementRequest = {
        service_type: serviceType,
        pickup_location: pickupLocation,
        dropoff_location: dropoffLocation,
        priority,
        contact_info: {
          name: 'Demo User',
          phone: '+1-555-0123'
        }
      };

      const job = await api.acceptQuote(quote.quote_id, request);
      setCurrentJob(job);
      setSelectedQuote(quote);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to accept quote');
    } finally {
      setLoading(false);
    }
  };

  const resetDemo = () => {
    setCurrentJob(null);
    setSelectedQuote(null);
    setQuotes([]);
    setAvailableWorkers([]);
    setError(null);
  };

  if (currentJob) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">Job Tracking</h2>
          <button
            onClick={resetDemo}
            className="btn-secondary flex items-center space-x-2"
          >
            <RefreshCw className="w-4 h-4" />
            <span>New Request</span>
          </button>
        </div>
        <JobTracker job={currentJob} onClose={resetDemo} />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-3xl font-bold text-gray-900 mb-4">
          Universal Movement API Demo
        </h2>
        <p className="text-lg text-gray-600 max-w-3xl mx-auto">
          Experience the power of Tesseracts World - the Plaid for gig economy. 
          Route anything, anywhere through a single API that connects all movement providers.
        </p>
      </div>

      {/* Service Type Selection */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Select Service Type</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {serviceTypeOptions.map((option) => {
            const Icon = option.icon;
            const isSelected = serviceType === option.value;
            
            return (
              <button
                key={option.value}
                onClick={() => setServiceType(option.value)}
                className={`
                  p-4 rounded-lg border-2 transition-all duration-200 text-left
                  ${isSelected 
                    ? 'border-primary-500 bg-primary-50 text-primary-700' 
                    : 'border-gray-200 hover:border-gray-300 text-gray-700'
                  }
                `}
              >
                <div className="flex items-center space-x-3 mb-2">
                  <Icon className="w-5 h-5" />
                  <span className="font-medium">{option.label}</span>
                </div>
                <p className="text-sm opacity-75">{option.description}</p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Location Selection */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="card">
          <LocationPicker
            label="Pickup Location"
            location={pickupLocation}
            onChange={setPickupLocation}
            placeholder="Where should we pick up?"
          />
        </div>
        
        <div className="card">
          <LocationPicker
            label="Dropoff Location"
            location={dropoffLocation}
            onChange={setDropoffLocation}
            placeholder="Where should we deliver?"
          />
        </div>
      </div>

      {/* Priority Selection */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Priority Level</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {priorityOptions.map((option) => {
            const isSelected = priority === option.value;
            
            return (
              <button
                key={option.value}
                onClick={() => setPriority(option.value)}
                className={`
                  p-4 rounded-lg border-2 transition-all duration-200 text-left
                  ${isSelected 
                    ? 'border-primary-500 bg-primary-50' 
                    : 'border-gray-200 hover:border-gray-300'
                  }
                `}
              >
                <div className={`font-medium mb-1 ${isSelected ? 'text-primary-700' : option.color}`}>
                  {option.label}
                </div>
                <p className="text-sm text-gray-600">{option.description}</p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Request Button */}
      <div className="text-center">
        <button
          onClick={handleRequestQuotes}
          disabled={!pickupLocation || !dropoffLocation || loading}
          className={`
            btn-primary px-8 py-3 text-lg flex items-center space-x-3 mx-auto
            ${loading ? 'opacity-50 cursor-not-allowed' : ''}
          `}
        >
          {loading ? (
            <>
              <RefreshCw className="w-5 h-5 animate-spin" />
              <span>Finding Options<span className="loading-dots"></span></span>
            </>
          ) : (
            <>
              <Search className="w-5 h-5" />
              <span>Find Movement Options</span>
            </>
          )}
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="card border-red-200 bg-red-50">
          <div className="flex items-center space-x-2 text-red-700">
            <AlertCircle className="w-5 h-5" />
            <span className="font-medium">Error</span>
          </div>
          <p className="text-red-600 mt-2">{error}</p>
        </div>
      )}

      {/* Quotes Display */}
      {quotes.length > 0 && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-semibold text-gray-900">
              Available Options ({quotes.length})
            </h3>
            <div className="text-sm text-gray-500">
              Quotes expire in 15-20 minutes
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {quotes.map((quote, index) => (
              <QuoteCard
                key={quote.quote_id}
                quote={quote}
                isRecommended={index === 0}
                onSelect={handleAcceptQuote}
                isSelected={selectedQuote?.quote_id === quote.quote_id}
              />
            ))}
          </div>
        </div>
      )}

      {/* Available Workers */}
      {availableWorkers.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center space-x-2">
            <Users className="w-5 h-5" />
            <span>Available Workers Nearby ({availableWorkers.length})</span>
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {availableWorkers.slice(0, 6).map((worker) => (
              <div key={worker.id} className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-gray-900">{worker.name}</span>
                  {worker.rating && (
                    <div className="flex items-center space-x-1">
                      <span className="text-sm text-gray-600">{worker.rating}</span>
                      <div className="w-1 h-1 bg-yellow-500 rounded-full"></div>
                    </div>
                  )}
                </div>
                
                <div className="space-y-1 text-sm text-gray-600">
                  {worker.vehicle && (
                    <div className="flex items-center space-x-2">
                      {worker.vehicle.type === 'bike' ? <Bike className="w-3 h-3" /> : 
                       worker.vehicle.type === 'truck' ? <Truck className="w-3 h-3" /> : 
                       <Car className="w-3 h-3" />}
                      <span className="capitalize">{worker.vehicle.type}</span>
                    </div>
                  )}
                  
                  {worker.distance_km && (
                    <div className="flex items-center space-x-2">
                      <MapPin className="w-3 h-3" />
                      <span>{worker.distance_km.toFixed(1)}km away</span>
                    </div>
                  )}
                  
                  <div className="text-xs text-gray-500 capitalize">
                    {worker.provider_id.replace('local_', '').replace('_', ' ')}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}