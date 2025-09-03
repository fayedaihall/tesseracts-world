import React, { useState, useEffect } from 'react';
import { Header } from './components/Layout/Header';
import { Dashboard } from './components/Dashboard/Dashboard';
import { MovementDemo } from './components/Movement/MovementDemo';
import { CommerceDemo } from './components/Commerce/CommerceDemo';
import { Globe, Zap, Activity, AlertCircle, RefreshCw, CheckCircle } from 'lucide-react';

function App() {
  const [currentSection, setCurrentSection] = useState('dashboard');
  const [apiStatus, setApiStatus] = useState<'checking' | 'online' | 'offline'>('checking');

  useEffect(() => {
    checkApiStatus();
  }, []);

  const checkApiStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/health');
      if (response.ok) {
        setApiStatus('online');
      } else {
        setApiStatus('offline');
      }
    } catch (error) {
      setApiStatus('offline');
    }
  };

  const renderCurrentSection = () => {
    switch (currentSection) {
      case 'dashboard':
        return <Dashboard />;
      case 'movement':
        return <MovementDemo />;
      case 'commerce':
        return <CommerceDemo />;
      default:
        return <Dashboard />;
    }
  };

  const getSectionIcon = (section: string) => {
    switch (section) {
      case 'dashboard':
        return Activity;
      case 'movement':
        return Globe;
      case 'commerce':
        return Zap;
      default:
        return Activity;
    }
  };

  const getSectionTitle = (section: string) => {
    switch (section) {
      case 'dashboard':
        return 'Dashboard';
      case 'movement':
        return 'Movement API';
      case 'commerce':
        return 'Commerce Platform';
      default:
        return 'Dashboard';
    }
  };

  const getSectionDescription = (section: string) => {
    switch (section) {
      case 'dashboard':
        return 'Real-time analytics and system overview';
      case 'movement':
        return 'Universal API for rideshare, delivery, and logistics';
      case 'commerce':
        return 'Decentralized marketplace with blockchain escrow';
      default:
        return '';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header onNavigate={setCurrentSection} currentSection={currentSection} />
      
      {/* API Status Banner */}
      {apiStatus === 'offline' && (
        <div className="bg-red-50 border-b border-red-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
            <div className="flex items-center space-x-2 text-red-700">
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm font-medium">
                API Server Offline - Please start the backend server: <code className="bg-red-100 px-1 rounded">python run.py</code>
              </span>
            </div>
          </div>
        </div>
      )}

      {apiStatus === 'online' && (
        <div className="bg-green-50 border-b border-green-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2">
            <div className="flex items-center space-x-2 text-green-700">
              <CheckCircle className="w-4 h-4" />
              <span className="text-sm">
                API Server Online - All systems operational
              </span>
            </div>
          </div>
        </div>
      )}

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Section Header */}
        <div className="mb-8">
          <div className="flex items-center space-x-3 mb-2">
            {React.createElement(getSectionIcon(currentSection), { 
              className: "w-8 h-8 text-primary-600" 
            })}
            <h1 className="text-3xl font-bold text-gray-900">
              {getSectionTitle(currentSection)}
            </h1>
          </div>
          <p className="text-lg text-gray-600">
            {getSectionDescription(currentSection)}
          </p>
        </div>

        {/* Section Content */}
        <div className="animate-fade-in">
          {apiStatus === 'online' ? (
            renderCurrentSection()
          ) : (
            <div className="card text-center py-12">
              <Globe className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-xl font-medium text-gray-900 mb-2">
                Waiting for API Server
              </h3>
              <p className="text-gray-600 mb-6">
                Start the Tesseracts World API server to begin the demo
              </p>
              <div className="bg-gray-100 rounded-lg p-4 max-w-md mx-auto">
                <code className="text-sm text-gray-800">
                  cd tesseracts-world<br />
                  python run.py
                </code>
              </div>
              <button
                onClick={checkApiStatus}
                className="btn-primary mt-6 flex items-center space-x-2 mx-auto"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Check Again</span>
              </button>
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center">
            <div className="flex items-center justify-center space-x-2 mb-4">
              <Globe className="w-6 h-6 text-primary-600" />
              <span className="text-lg font-semibold text-gray-900">Tesseracts World</span>
            </div>
            <p className="text-gray-600 mb-4">
              The Universal API for Movement - Route anything, anywhere through the gig economy
            </p>
            <div className="flex items-center justify-center space-x-6 text-sm text-gray-500">
              <span>🌍 Global Coverage</span>
              <span>⚡ Real-time Tracking</span>
              <span>🔒 Blockchain Escrow</span>
              <span>🤖 AI Optimization</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;