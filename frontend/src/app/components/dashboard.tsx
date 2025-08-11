import React, { useState, useEffect } from 'react';
import { useUser } from '@clerk/nextjs';
import { Calendar, Clock, FileText, Activity, AlertCircle, CheckCircle, RefreshCw, Trash2 } from 'lucide-react';

interface UserScheduleInfo {
  user_id: string;
  schedule_active: boolean;
  schedule_type?: string;
  next_execution?: string;
  chunks_remaining?: number;
  progress?: {
    processed_count: number;
    current_index: number;
    last_processed: string;
  };
}

interface UserInsights {
  user_id: string;
  insights: Array<{
    chunk_index: number;
    insight?: string;
    error?: string;
  }>;
  retrieved_at: string;
}

interface TaskStatus {
  task_id: string;
  status: string;
  result?: any;
  progress?: any;
  error?: string;
}

const Dashboard = () => {
  const { user, isLoaded } = useUser();
  const [scheduleInfo, setScheduleInfo] = useState<UserScheduleInfo | null>(null);
  const [insights, setInsights] = useState<UserInsights | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = async () => {
    if (!user?.id) {
      setLoading(false);
      return;
    }

    try {
      setError(null);
      
      // Fetch schedule info
      const scheduleResponse = await fetch(`/api/user-schedule/${user.id}`);
      if (scheduleResponse.ok) {
        const scheduleData = await scheduleResponse.json();
        setScheduleInfo(scheduleData);
      } else if (scheduleResponse.status === 401) {
        setError('Authentication required. Please sign in.');
        return;
      }

      // Fetch insights
      const insightsResponse = await fetch(`/api/user-insights/${user.id}`);
      if (insightsResponse.ok) {
        const insightsData = await insightsResponse.json();
        setInsights(insightsData);
      } else if (insightsResponse.status === 404) {
        // 404 is expected if no insights exist yet
        console.log('No insights found yet - this is normal for new users');
      } else if (insightsResponse.status === 401) {
        setError('Authentication required. Please sign in.');
        return;
      } else {
        console.warn('Failed to fetch insights:', insightsResponse.status);
      }

    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchData();
  };

  const handleCancelSchedule = async () => {
    if (!user?.id || !scheduleInfo?.schedule_active) return;

    try {
      const response = await fetch(`/api/user-schedule/${user.id}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        await fetchData(); // Refresh data
      } else {
        const errorData = await response.json();
        setError(errorData.error || 'Failed to cancel schedule');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel schedule');
    }
  };

  useEffect(() => {
    if (isLoaded) {
      fetchData();
    }
  }, [user?.id, isLoaded]);

  if (!isLoaded || loading) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-gray-600">
            {!isLoaded ? 'Loading authentication...' : 'Loading dashboard...'}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600">Monitor your PDF processing status and insights</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-400 transition-colors"
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center">
          <AlertCircle className="h-5 w-5 text-red-500 mr-2" />
          <span className="text-red-700">{error}</span>
        </div>
      )}

      {/* Schedule Status */}
      <div className="bg-white shadow-lg rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4 flex items-center">
          <Calendar className="mr-2 h-5 w-5" />
          Schedule Status
        </h2>
        
        {scheduleInfo ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                {scheduleInfo.schedule_active ? (
                  <CheckCircle className="h-5 w-5 text-green-500 mr-2" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-gray-400 mr-2" />
                )}
                <span className={`font-medium ${scheduleInfo.schedule_active ? 'text-green-700' : 'text-gray-500'}`}>
                  {scheduleInfo.schedule_active ? 'Active Schedule' : 'No Active Schedule'}
                </span>
              </div>
              
              {scheduleInfo.schedule_active && (
                <button
                  onClick={handleCancelSchedule}
                  className="flex items-center px-3 py-1 bg-red-100 text-red-700 rounded-md hover:bg-red-200 transition-colors text-sm"
                >
                  <Trash2 className="mr-1 h-4 w-4" />
                  Cancel
                </button>
              )}
            </div>

            {scheduleInfo.schedule_active && (
              <div className="grid md:grid-cols-2 gap-4 pt-4 border-t">
                <div>
                  <p className="text-sm text-gray-600">Schedule Type</p>
                  <p className="font-medium capitalize">{scheduleInfo.schedule_type?.toLowerCase().replace('_', ' ')}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Next Execution</p>
                  <p className="font-medium">
                    {scheduleInfo.next_execution 
                      ? new Date(scheduleInfo.next_execution).toLocaleString()
                      : 'Not scheduled'
                    }
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Chunks Remaining</p>
                  <p className="font-medium">{scheduleInfo.chunks_remaining || 0}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Processed Count</p>
                  <p className="font-medium">{scheduleInfo.progress?.processed_count || 0}</p>
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-gray-500">No schedule information available</p>
        )}
      </div>

      {/* Insights Status */}
      <div className="bg-white shadow-lg rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4 flex items-center">
          <FileText className="mr-2 h-5 w-5" />
          Generated Insights
        </h2>
        
        {insights ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900">
                  {insights.insights.length} insights generated
                </p>
                <p className="text-sm text-gray-600">
                  Last updated: {new Date(insights.retrieved_at).toLocaleString()}
                </p>
              </div>
            </div>

            <div className="space-y-2 max-h-64 overflow-y-auto">
              {insights.insights.map((insight, index) => (
                <div key={index} className="p-3 bg-gray-50 rounded-md">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700">
                      Chunk {insight.chunk_index + 1}
                    </span>
                    {insight.error ? (
                      <span className="text-xs text-red-600 bg-red-100 px-2 py-1 rounded">
                        Error
                      </span>
                    ) : (
                      <span className="text-xs text-green-600 bg-green-100 px-2 py-1 rounded">
                        Complete
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-600 line-clamp-3">
                    {insight.insight || insight.error || 'No content available'}
                  </p>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-gray-500">No insights generated yet</p>
        )}
      </div>

      {/* Health Check */}
      <div className="bg-white shadow-lg rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4 flex items-center">
          <Activity className="mr-2 h-5 w-5" />
          System Status
        </h2>
        <HealthCheck />
      </div>
    </div>
  );
};

// Health Check Component
const HealthCheck = () => {
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch('/api/health');
        if (response.ok) {
          const data = await response.json();
          setHealth(data);
        }
      } catch (err) {
        console.error('Health check failed:', err);
      } finally {
        setLoading(false);
      }
    };

    checkHealth();
  }, []);

  if (loading) {
    return <div className="text-gray-500">Checking system status...</div>;
  }

  if (!health) {
    return <div className="text-red-500">Unable to connect to backend services</div>;
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="font-medium">Overall Status</span>
        <span className={`px-2 py-1 rounded text-sm ${
          health.status === 'healthy' 
            ? 'bg-green-100 text-green-700' 
            : 'bg-yellow-100 text-yellow-700'
        }`}>
          {health.status}
        </span>
      </div>
      
      {health.services && (
        <div className="space-y-1">
          {Object.entries(health.services).map(([service, status]) => (
            <div key={service} className="flex items-center justify-between text-sm">
              <span className="capitalize">{service}</span>
              <span className={`px-2 py-1 rounded text-xs ${
                status === 'healthy' 
                  ? 'bg-green-100 text-green-600' 
                  : 'bg-red-100 text-red-600'
              }`}>
                {status as string}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Dashboard;