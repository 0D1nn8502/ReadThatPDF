'use client';

import { Fira_Mono, Montserrat } from "next/font/google";
import { useState } from "react";
import { SignedIn, SignedOut, SignInButton } from "@clerk/nextjs";
import dynamic from "next/dynamic";

const montserrat = Montserrat({
  weight: "500",
  subsets: ['latin'],
  display: 'swap'
});

const firamono = Fira_Mono({
  weight: "500",
  subsets: ['latin'],
  display: 'swap'
});

// Dynamic imports for better code splitting
const PDFRangeExtractor = dynamic(
  () => import('@/app/components/pdfRange'),
  { ssr: false }
);

const PDFProcessorForm = dynamic(
  () => import('@/app/components/processing-form'),
  { ssr: false }
);

const Dashboard = dynamic(
  () => import('@/app/components/dashboard'),
  { ssr: false }
);

type Tab = 'extract' | 'process' | 'dashboard';

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');
  const [extractedText, setExtractedText] = useState<string>('');

  const handleTextExtracted = (text: string) => {
    setExtractedText(text);
    // Automatically switch to processing tab when text is extracted
    setActiveTab('process');
  };

  return (
    <div className={`min-h-screen bg-gray-50 ${firamono.className}`}>
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <h1 className={`text-3xl font-bold text-gray-900 ${montserrat.className}`}>
            PDF Processing Platform
          </h1>
          <p className="text-gray-600 mt-2">
            Extract text from PDFs and set up intelligent processing workflows
          </p>
        </div>
      </div>

      {/* Authentication Check */}
      <SignedOut>
        <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
          <div className="text-center max-w-md">
            <div className="mb-8">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <h2 className={`text-2xl font-bold text-gray-900 mb-4 ${montserrat.className}`}>
                Welcome to PDF Processor
              </h2>
              <p className="text-gray-600 mb-6">
                Sign in to access PDF text extraction and intelligent processing features. 
                Set up scheduled deliveries and get insights from your documents.
              </p>
            </div>
            <SignInButton>
              <button className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-8 rounded-lg transition-colors duration-200 shadow-sm">
                Sign In to Get Started
              </button>
            </SignInButton>
          </div>
        </div>
      </SignedOut>

      {/* Main Content - Only shown when signed in */}
      <SignedIn>
        <div className="max-w-6xl mx-auto px-4 py-6">
          {/* Tab Navigation */}
          <div className="mb-8">
            <div className="border-b border-gray-200">
              <nav className="-mb-px flex space-x-8">
                <button
                  onClick={() => setActiveTab('dashboard')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors duration-200 ${
                    activeTab === 'dashboard'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  📊 Dashboard
                </button>
                <button
                  onClick={() => setActiveTab('extract')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors duration-200 ${
                    activeTab === 'extract'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  📄 Extract PDF Text
                </button>
                <button
                  onClick={() => setActiveTab('process')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors duration-200 ${
                    activeTab === 'process'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  ⚙️ Process & Schedule
                  {extractedText && (
                    <span className="ml-2 inline-block w-2 h-2 bg-green-500 rounded-full"></span>
                  )}
                </button>
              </nav>
            </div>
          </div>

          {/* Tab Content */}
          <div className="transition-opacity duration-200">
            {activeTab === 'dashboard' && (
              <div>
                <div className="mb-6">
                  <h2 className={`text-xl font-semibold text-gray-900 mb-2 ${montserrat.className}`}>
                    Your Processing Dashboard
                  </h2>
                  <p className="text-gray-600">
                    Monitor your PDF processing status, schedules, and generated insights.
                  </p>
                </div>
                <Dashboard />
              </div>
            )}

            {activeTab === 'extract' && (
              <div>
                <div className="mb-6">
                  <h2 className={`text-xl font-semibold text-gray-900 mb-2 ${montserrat.className}`}>
                    Extract Text from PDF
                  </h2>
                  <p className="text-gray-600">
                    Upload a PDF file and specify the page range to extract text content.
                  </p>
                </div>
                <PDFRangeExtractor onTextExtracted={handleTextExtracted} />
              </div>
            )}

            {activeTab === 'process' && (
              <div>
                <div className="mb-6">
                  <h2 className={`text-xl font-semibold text-gray-900 mb-2 ${montserrat.className}`}>
                    Process & Schedule Content
                  </h2>
                  <p className="text-gray-600">
                    Configure how your extracted content should be processed and delivered.
                  </p>
                  {!extractedText && (
                    <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                      <p className="text-yellow-800 text-sm">
                        💡 <strong>Tip:</strong> Extract text from a PDF first, or paste your content directly in the form below.
                      </p>
                    </div>
                  )}
                </div>
                <PDFProcessorForm initialText={extractedText} />
              </div>
            )}
          </div>
        </div>
      </SignedIn>
    </div>
  );
}