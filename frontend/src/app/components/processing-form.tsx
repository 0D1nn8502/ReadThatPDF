import React, { useState, useEffect } from 'react';
import { Calendar, Clock, FileText, Settings, Send, AlertCircle, CheckCircle } from 'lucide-react';
import { useUser, SignedIn, SignedOut, SignInButton } from '@clerk/nextjs';


interface PDFProcessorFormProps {
  initialText?: string;
}


const PDFProcessorForm = ({ initialText = '' }: PDFProcessorFormProps) => {
  const { user, isLoaded } = useUser();
  const [formData, setFormData] = useState({
    // PDF Text (from your extraction)
    text: initialText, 
    
    // Processing Configuration
    processing_mode: 'immediate_only', // immediate_only, schedule_only, immediate_and_schedule
    immediate_chunks_count: 2,
    chunks_per_delivery: 2,
    
    // Scheduling Information
    schedule_type: 'daily', // daily, weekly, twice_daily, every_two_days, monthly
    schedule_time: '09:00',
    user_timezone: 'Asia/Kolkata',
    
    // Custom scheduling (for CUSTOM schedule_type)
    custom_interval_hours: 24,
  });

  // Update text when initialText changes
  useEffect(() => {
    if (initialText) {
      setFormData(prev => ({ ...prev, text: initialText }));
    }
  }, [initialText]);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);

  const handleInputChange = (e) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'number' ? parseInt(value) || 0 : value
    }));
  };

  const handleSubmit = async () => {
    if (!user) {
      setSubmitResult({ success: false, error: 'Please sign in to continue' });
      return;
    }

    setIsSubmitting(true);
    setSubmitResult(null);

    try {
      // Validate required fields
      if (!formData.text.trim()) {
        throw new Error('PDF text is required. Please extract text first.');
      }

      // Prepare the request payload (userId and email automatically from Clerk)
      const payload = {
        text: formData.text,
        processing_mode: formData.processing_mode,
        immediate_chunks_count: formData.immediate_chunks_count,
        chunks_per_delivery: formData.chunks_per_delivery,
        schedule_type: formData.schedule_type,
        schedule_time: formData.schedule_time,
        user_timezone: formData.user_timezone,
        custom_interval_hours: formData.custom_interval_hours 
      };

      // Add custom interval if schedule type is CUSTOM
      if (formData.schedule_type === 'CUSTOM') {
        payload.custom_interval_hours = formData.custom_interval_hours;
      }

      console.log('Submitting payload:', payload);

      // Make the API call to your process-pdf-text endpoint
      const response = await fetch('/api/process-pdf-text', {
        method: 'POST',
        credentials: 'include',  
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      const result = await response.json();
      setSubmitResult({ success: true, data: result });
      
    } catch (error) {
      console.error('Error submitting form:', error);
      setSubmitResult({ success: false, error: error.message });
    } finally {
      setIsSubmitting(false);
    }
  };

  const processingModes = [
    { value: 'immediate_only', label: 'Process Immediately Only', description: 'Process chunks right away, no scheduling' },
    { value: 'schedule_only', label: 'Schedule Only', description: 'Only set up scheduled processing' },
    { value: 'immediate_and_schedule', label: 'Both Immediate & Scheduled', description: 'Process some now, schedule the rest' }
  ];

  const scheduleTypes = [
    { value: 'daily', label: 'Daily', description: 'Send chunks every day' },
    { value: 'weekly', label: 'Weekly', description: 'Send chunks once per week' },
    { value: 'twice_daily', label: 'Twice Daily', description: 'Send chunks twice per day' },
    { value: 'every_two_days', label: 'Every Two Days', description: 'Send chunks every other day' },
    { value: 'monthly', label: 'Monthly', description: 'Send chunks once per month' }
  ];

  const timezones = [
    'Asia/Kolkata',
    'America/New_York',
    'America/Los_Angeles',
    'Europe/London',
    'Europe/Berlin',
    'Asia/Tokyo',
    'Australia/Sydney',
    'UTC'
  ];

  // Show loading spinner while checking auth
  if (!isLoaded) {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-white shadow-lg rounded-lg">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white shadow-lg rounded-lg">
      <SignedOut>
        <div className="text-center py-12">
          <AlertCircle className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Authentication Required</h2>
          <p className="text-gray-600 mb-6">Please sign in to access PDF processing features</p>
          <SignInButton>
            <button className="bg-blue-600 text-white px-6 py-3 rounded-md font-medium hover:bg-blue-700 transition-colors">
              Sign In to Continue
            </button>
          </SignInButton>
        </div>
      </SignedOut>

      <SignedIn>
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">PDF Processing & Scheduling</h1>
          <p className="text-gray-600">Configure how your PDF content should be processed and delivered</p>
          
          {/* User Info Display */}
          <div className="mt-4 p-4 bg-blue-50 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Signed in as:</p>
                <p className="font-medium text-gray-900">{user?.primaryEmailAddress?.emailAddress}</p>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-600">User ID:</p>
                <p className="font-mono text-sm text-gray-900">{user?.id}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-8">
          {/* PDF Content Section */}
          <div className="bg-gray-50 p-6 rounded-lg">
            <h2 className="text-xl font-semibold mb-4 flex items-center">
              <FileText className="mr-2" size={20} />
              PDF Content
            </h2>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Extracted Text *
              </label>
              <textarea
                name="text"
                value={formData.text}
                onChange={handleInputChange}
                rows={8}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Paste your extracted PDF text here..."
                required
              />
              <p className="text-sm text-gray-500 mt-1">
                Character count: {formData.text.length.toLocaleString()}
              </p>
            </div>
          </div>

          {/* Processing Configuration */}
          <div className="bg-gray-50 p-6 rounded-lg">
            <h2 className="text-xl font-semibold mb-4 flex items-center">
              <Settings className="mr-2" size={20} />
              Processing Configuration
            </h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Processing Mode
                </label>
                <div className="space-y-2">
                  {processingModes.map(mode => (
                    <label key={mode.value} className="flex items-start cursor-pointer">
                      <input
                        type="radio"
                        name="processing_mode"
                        value={mode.value}
                        checked={formData.processing_mode === mode.value}
                        onChange={handleInputChange}
                        className="mt-1 mr-3"
                      />
                      <div>
                        <div className="font-medium text-gray-900">{mode.label}</div>
                        <div className="text-sm text-gray-600">{mode.description}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {(formData.processing_mode === 'immediate_only' || formData.processing_mode === 'immediate_and_schedule') && (
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Immediate Chunks Count
                    </label>
                    <input
                      type="number"
                      name="immediate_chunks_count"
                      value={formData.immediate_chunks_count}
                      onChange={handleInputChange}
                      min="1"
                      max="10"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <p className="text-sm text-gray-500 mt-1">Number of chunks to process immediately</p>
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Chunks Per Delivery
                </label>
                <input
                  type="number"
                  name="chunks_per_delivery"
                  value={formData.chunks_per_delivery}
                  onChange={handleInputChange}
                  min="1"
                  max="10"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-sm text-gray-500 mt-1">How many chunks to process in each scheduled batch</p>
              </div>
            </div>
          </div>

          {/* Scheduling Section */}
          {(formData.processing_mode === 'schedule_only' || formData.processing_mode === 'immediate_and_schedule') && (
            <div className="bg-gray-50 p-6 rounded-lg">
              <h2 className="text-xl font-semibold mb-4 flex items-center">
                <Calendar className="mr-2" size={20} />
                Scheduling Configuration
              </h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Schedule Type
                  </label>
                  <div className="space-y-2">
                    {scheduleTypes.map(type => (
                      <label key={type.value} className="flex items-start cursor-pointer">
                        <input
                          type="radio"
                          name="schedule_type"
                          value={type.value}
                          checked={formData.schedule_type === type.value}
                          onChange={handleInputChange}
                          className="mt-1 mr-3"
                        />
                        <div>
                          <div className="font-medium text-gray-900">{type.label}</div>
                          <div className="text-sm text-gray-600">{type.description}</div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 flex items-center">
                      <Clock className="mr-1" size={16} />
                      Schedule Time
                    </label>
                    <input
                      type="time"
                      name="schedule_time"
                      value={formData.schedule_time}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Timezone
                    </label>
                    <select
                      name="user_timezone"
                      value={formData.user_timezone}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {timezones.map(tz => (
                        <option key={tz} value={tz}>{tz}</option>
                      ))}
                    </select>
                  </div>
                </div>


              </div>
            </div>
          )}

          {/* Submit Section */}
          <div className="flex items-center justify-between pt-6 border-t border-gray-200">
            <div className="text-sm text-gray-600">
              Make sure all information is correct before submitting
            </div>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={isSubmitting || !formData.text.trim()}
              className="flex items-center px-6 py-3 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="mr-2" size={16} />
              {isSubmitting ? 'Processing...' : 'Start Processing'}
            </button>
          </div>
        </div>

        {/* Results Section */}
        {submitResult && (
          <div className={`mt-8 p-6 rounded-lg ${submitResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
            <h3 className={`text-lg font-semibold mb-2 flex items-center ${submitResult.success ? 'text-green-800' : 'text-red-800'}`}>
              {submitResult.success ? <CheckCircle className="mr-2" size={20} /> : <AlertCircle className="mr-2" size={20} />}
              {submitResult.success ? 'Success!' : 'Error'}
            </h3>
            {submitResult.success ? (
              <div className="space-y-2 text-green-700">
                <p><strong>Status:</strong> {submitResult.data.status}</p>
                <p><strong>Total Chunks:</strong> {submitResult.data.total_chunks}</p>
                <p><strong>Immediate Processing:</strong> {submitResult.data.chunks_processed_immediately} chunks</p>
                <p><strong>Schedule Set:</strong> {submitResult.data.schedule_set ? 'Yes' : 'No'}</p>
                {submitResult.data.immediate_task_id && (
                  <p><strong>Task ID:</strong> {submitResult.data.immediate_task_id}</p>
                )}
              </div>
            ) : (
              <p className="text-red-700">{submitResult.error}</p>
            )}
          </div>
        )}
      </SignedIn>
    </div>
  );
};

export default PDFProcessorForm;