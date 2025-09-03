import React, { useState } from 'react';
import { MapPin, Navigation } from 'lucide-react';
import { Location } from '../../types';

interface LocationPickerProps {
  label: string;
  location: Location | null;
  onChange: (location: Location) => void;
  placeholder?: string;
}

export function LocationPicker({ label, location, onChange, placeholder }: LocationPickerProps) {
  const [address, setAddress] = useState(location?.address || '');

  // Predefined locations for demo
  const demoLocations = [
    {
      name: 'Downtown San Francisco',
      latitude: 37.7749,
      longitude: -122.4194,
      address: '123 Market St, San Francisco, CA 94105'
    },
    {
      name: 'Mission District',
      latitude: 37.7599,
      longitude: -122.4148,
      address: '456 Mission St, San Francisco, CA 94110'
    },
    {
      name: 'SoMa',
      latitude: 37.7849,
      longitude: -122.4094,
      address: '789 Howard St, San Francisco, CA 94103'
    },
    {
      name: 'Financial District',
      latitude: 37.7946,
      longitude: -122.3999,
      address: '321 Montgomery St, San Francisco, CA 94104'
    },
    {
      name: 'SFO Airport',
      latitude: 37.6213,
      longitude: -122.3790,
      address: 'San Francisco International Airport, CA 94128'
    }
  ];

  const handleLocationSelect = (demoLocation: typeof demoLocations[0]) => {
    const newLocation: Location = {
      latitude: demoLocation.latitude,
      longitude: demoLocation.longitude,
      address: demoLocation.address,
      city: 'San Francisco',
      state: 'CA',
      country: 'USA'
    };
    
    setAddress(demoLocation.address);
    onChange(newLocation);
  };

  const getCurrentLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const newLocation: Location = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            address: 'Current Location'
          };
          setAddress('Current Location');
          onChange(newLocation);
        },
        (error) => {
          console.error('Error getting location:', error);
        }
      );
    }
  };

  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-gray-700">
        {label}
      </label>
      
      <div className="relative">
        <MapPin className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
        <input
          type="text"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          placeholder={placeholder || 'Enter address or select from options'}
          className="input-field pl-10 pr-12"
        />
        <button
          onClick={getCurrentLocation}
          className="absolute right-3 top-2.5 p-1 text-gray-400 hover:text-primary-600 transition-colors"
          title="Use current location"
        >
          <Navigation className="w-4 h-4" />
        </button>
      </div>

      {/* Demo Location Quick Select */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {demoLocations.map((loc) => (
          <button
            key={loc.name}
            onClick={() => handleLocationSelect(loc)}
            className={`
              text-left p-3 rounded-lg border transition-all duration-200 hover:shadow-sm
              ${location?.latitude === loc.latitude && location?.longitude === loc.longitude
                ? 'border-primary-500 bg-primary-50 text-primary-700'
                : 'border-gray-200 hover:border-gray-300 text-gray-700'
              }
            `}
          >
            <div className="font-medium text-sm">{loc.name}</div>
            <div className="text-xs text-gray-500 mt-1">{loc.address}</div>
          </button>
        ))}
      </div>

      {location && (
        <div className="text-xs text-gray-500 bg-gray-50 p-2 rounded">
          Selected: {location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}
        </div>
      )}
    </div>
  );
}