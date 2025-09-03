import React from 'react';
import { Clock, DollarSign, Star, Car, Bike, Truck, User } from 'lucide-react';
import { Quote } from '../../types';
import { formatDistanceToNow } from 'date-fns';

interface QuoteCardProps {
  quote: Quote;
  isRecommended?: boolean;
  onSelect: (quote: Quote) => void;
  isSelected?: boolean;
}

export function QuoteCard({ quote, isRecommended, onSelect, isSelected }: QuoteCardProps) {
  const getProviderIcon = (providerId: string) => {
    if (providerId.includes('uber')) return Car;
    if (providerId.includes('bike') || providerId.includes('cycle')) return Bike;
    if (providerId.includes('truck') || providerId.includes('freight')) return Truck;
    return Car;
  };

  const getVehicleIcon = (vehicleType?: string) => {
    switch (vehicleType?.toLowerCase()) {
      case 'bike':
      case 'bicycle':
        return Bike;
      case 'truck':
      case 'van':
        return Truck;
      case 'car':
      default:
        return Car;
    }
  };

  const ProviderIcon = getProviderIcon(quote.provider_id);
  const VehicleIcon = quote.worker_info?.vehicle ? getVehicleIcon(quote.worker_info.vehicle.type) : ProviderIcon;

  const pickupTime = new Date(quote.estimated_pickup_time);
  const deliveryTime = new Date(quote.estimated_delivery_time);

  return (
    <div 
      className={`
        card cursor-pointer transition-all duration-200 hover:shadow-lg
        ${isSelected ? 'ring-2 ring-primary-500 border-primary-200' : 'hover:border-gray-300'}
        ${isRecommended ? 'border-green-200 bg-green-50' : ''}
      `}
      onClick={() => onSelect(quote)}
    >
      {isRecommended && (
        <div className="flex items-center space-x-1 mb-3">
          <Star className="w-4 h-4 text-green-600 fill-current" />
          <span className="text-sm font-medium text-green-700">Recommended</span>
        </div>
      )}

      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-gray-100 rounded-lg">
            <ProviderIcon className="w-5 h-5 text-gray-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 capitalize">
              {quote.provider_id.replace('local_', '').replace('_', ' ')}
            </h3>
            <p className="text-sm text-gray-500 capitalize">{quote.service_type}</p>
          </div>
        </div>
        
        <div className="text-right">
          <div className="text-2xl font-bold text-gray-900">
            ${quote.estimated_cost.toFixed(2)}
          </div>
          <div className="text-sm text-gray-500">
            {quote.estimated_duration_minutes}min
          </div>
        </div>
      </div>

      {/* Timing Information */}
      <div className="space-y-2 mb-4">
        <div className="flex items-center space-x-2 text-sm">
          <Clock className="w-4 h-4 text-gray-400" />
          <span className="text-gray-600">
            Pickup: {formatDistanceToNow(pickupTime, { addSuffix: true })}
          </span>
        </div>
        <div className="flex items-center space-x-2 text-sm">
          <MapPin className="w-4 h-4 text-gray-400" />
          <span className="text-gray-600">
            Delivery: {formatDistanceToNow(deliveryTime, { addSuffix: true })}
          </span>
        </div>
      </div>

      {/* Worker Information */}
      {quote.worker_info && (
        <div className="border-t border-gray-100 pt-3">
          <div className="flex items-center space-x-3">
            <div className="p-1.5 bg-gray-100 rounded-lg">
              <VehicleIcon className="w-4 h-4 text-gray-600" />
            </div>
            <div className="flex-1">
              <div className="flex items-center space-x-2">
                <span className="font-medium text-gray-900">{quote.worker_info.name}</span>
                {quote.worker_info.rating && (
                  <div className="flex items-center space-x-1">
                    <Star className="w-3 h-3 text-yellow-500 fill-current" />
                    <span className="text-sm text-gray-600">{quote.worker_info.rating}</span>
                  </div>
                )}
              </div>
              {quote.worker_info.vehicle && (
                <p className="text-sm text-gray-500 capitalize">
                  {quote.worker_info.vehicle.type}
                  {quote.worker_info.vehicle.license_plate && 
                    ` • ${quote.worker_info.vehicle.license_plate}`
                  }
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Confidence Score */}
      <div className="mt-3 pt-3 border-t border-gray-100">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Confidence</span>
          <div className="flex items-center space-x-2">
            <div className="w-16 bg-gray-200 rounded-full h-1.5">
              <div 
                className="bg-primary-600 h-1.5 rounded-full transition-all duration-300"
                style={{ width: `${quote.confidence_score * 100}%` }}
              ></div>
            </div>
            <span className="text-gray-900 font-medium">
              {Math.round(quote.confidence_score * 100)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}