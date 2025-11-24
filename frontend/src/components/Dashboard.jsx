import React, { useState, useEffect } from 'react';
import { healthCheck } from '../services/api';

export default function Dashboard() {
  const [healthStatus, setHealthStatus] = useState(null);

  useEffect(() => {
    checkHealth();
  }, []);

  const checkHealth = async () => {
    try {
      const response = await healthCheck();
      setHealthStatus(response.data);
    } catch (err) {
      setHealthStatus({ status: 'unhealthy', error: err.message });
    }
  };

  return (
    <div>
      <h2 className="text-3xl font-bold text-gray-800 mb-6">Dashboard</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm font-medium">API Status</p>
              <p className={`text-2xl font-bold mt-2 ${
                healthStatus?.status === 'healthy' ? 'text-green-600' : 'text-red-600'
              }`}>
                {healthStatus?.status || 'Checking...'}
              </p>
            </div>
            <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
              healthStatus?.status === 'healthy' ? 'bg-green-100' : 'bg-red-100'
            }`}>
              <svg className={`w-6 h-6 ${
                healthStatus?.status === 'healthy' ? 'text-green-600' : 'text-red-600'
              }`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          {healthStatus?.timestamp && (
            <p className="text-xs text-gray-400 mt-2">
              Last checked: {new Date(healthStatus.timestamp).toLocaleTimeString()}
            </p>
          )}
        </div>

        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm font-medium">Backend</p>
              <p className="text-xl font-bold mt-2 text-primary">AWS ALB</p>
            </div>
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
              </svg>
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-2">Auto Scaling + Load Balancing</p>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm font-medium">Database</p>
              <p className="text-xl font-bold mt-2 text-secondary">DynamoDB</p>
            </div>
            <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
              </svg>
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-2">NoSQL Cloud Database</p>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-xl font-semibold mb-4">Quick Start</h3>
        <div className="space-y-3">
          <div className="flex items-start">
            <span className="bg-primary text-white rounded-full w-6 h-6 flex items-center justify-center text-sm mr-3 mt-0.5">1</span>
            <div>
              <p className="font-medium">Add Courses</p>
              <p className="text-sm text-gray-600">Navigate to Courses tab and create new courses</p>
            </div>
          </div>
          <div className="flex items-start">
            <span className="bg-primary text-white rounded-full w-6 h-6 flex items-center justify-center text-sm mr-3 mt-0.5">2</span>
            <div>
              <p className="font-medium">Register Students</p>
              <p className="text-sm text-gray-600">Go to Students tab to add student profiles</p>
            </div>
          </div>
          <div className="flex items-start">
            <span className="bg-primary text-white rounded-full w-6 h-6 flex items-center justify-center text-sm mr-3 mt-0.5">3</span>
            <div>
              <p className="font-medium">Create Enrollments</p>
              <p className="text-sm text-gray-600">Enroll students in courses from the Enrollments tab</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
