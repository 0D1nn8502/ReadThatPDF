import React, { useState, useRef } from 'react';
import { Upload, FileText, Download, AlertCircle, Scissors, Sparkles, Brain, Loader } from 'lucide-react';


interface PDFRangeExtractorProps {
  onTextExtracted?: (text: string) => void;
}


export const PDFRangeExtractor: React.FC <PDFRangeExtractorProps> = ({ onTextExtracted }) => {
  const [file, setFile] = useState<File | null>(null);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [startPage, setStartPage] = useState<number>(1);
  const [endPage, setEndPage] = useState<number>(1);
  const [extractedText, setExtractedText] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [insights, setInsights] = useState<string>('');
  const [insightsLoading, setInsightsLoading] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null); 

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const uploadedFile = event.target.files?.[0];
    if (uploadedFile && uploadedFile.type === 'application/pdf') {
      setFile(uploadedFile);
      setError('');
      setExtractedText('');
      setInsights('');
      setStartPage(1);
      setEndPage(1);
      setNumPages(null);
      setLoading(false); 
    } else {
      setError('Please upload a valid PDF file');
    }
  };

  const extractText = async () => {
    if (!file) return;
    setLoading(true);  
    setError('');

    try {
      const formData = new FormData();
      formData.append('pdf', file);
      formData.append('startPage', startPage.toString());
      formData.append('endPage', endPage.toString());

      const response = await fetch('/api/extract-text', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to extract text');
      }

      const data = await response.json();
      const text = data.text; 

      setExtractedText(text); 

      // Notify parent component // 
      if (onTextExtracted) {
        onTextExtracted(text);
      }


    } catch (err) {
      setError('Error extracting text: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      setLoading(false);
    }
  };

  const generateInsights = async () => {
    if (!extractedText) return;
    setInsightsLoading(true);
    setError('');

    try {
      const response = await fetch('/api/generate-insights', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: extractedText,
          pages: `${startPage}-${endPage}`
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to generate insights');
      }

      const data = await response.json();
      setInsights(data.insights);
    } catch (err) {
      setError('Error generating insights: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      setInsightsLoading(false);
    }
  };

  const downloadText = () => {
    if (!extractedText) return;
    const blob = new Blob([extractedText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `extracted-text-pages-${startPage}-${endPage}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadInsights = () => {
    if (!insights) return;
    const blob = new Blob([insights], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `insights-pages-${startPage}-${endPage}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const resetSelection = () => {
    setStartPage(1);
    setEndPage(numPages || 1);
  };

  const handleStartPageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value);
    if (!isNaN(value) && value >= 1 && (!numPages || value <= numPages)) {
      setStartPage(value);
      if (value > endPage) {
        setEndPage(value);
      }
    }
  };

  const handleEndPageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value);
    if (!isNaN(value) && value >= startPage && (!numPages || value <= numPages)) {
      setEndPage(value);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-100 via-blue-50 to-indigo-100 p-4">
      <div className="max-w-7xl mx-auto">
        <div className="bg-white/80 backdrop-blur-sm rounded-3xl shadow-2xl overflow-hidden border border-white/20">
          {/* Header */}
          <div className="bg-black text-white p-8 relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-r from-purple-600/20 via-blue-600/20 to-indigo-600/20 animate-pulse"></div>
            <div className="relative z-10">
              <h1 className="text-4xl font-bold flex items-center gap-4 mb-2">
                <div className="relative">
                  <FileText className="w-10 h-10" />
                  <Sparkles className="w-4 h-4 absolute -top-1 -right-1 text-yellow-300 animate-pulse" />
                </div>
                Read that PDF
              </h1>
              <p className="text-blue-100 text-lg">
                Upload and extract text from any PDF with precision
              </p>
            </div>
          </div>

          <div className="p-8">
            {/* File Upload */}
            <div className="mb-10">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                onChange={handleFileUpload}
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}         
                className="group w-full border-3 border-dashed border-purple-300 rounded-2xl p-12 text-center hover:border-purple-400 hover:bg-gradient-to-br hover:from-purple-50 hover:to-blue-50 transition-all duration-300 transform hover:scale-[1.02]"
              >
                <Upload className="w-16 h-16 mx-auto mb-6 text-purple-400 group-hover:text-purple-600 transition-colors group-hover:animate-bounce" />
                <p className="text-xl font-semibold text-gray-700 mb-2">
                  {file ? file.name : 'Click to upload PDF file'}
                </p>
                <p className="text-gray-500">PDF files only, up to 10MB</p>
              </button>
            </div>

            {error && (
              <div className="mb-8 p-5 bg-gradient-to-r from-red-50 to-pink-50 border border-red-200 rounded-xl flex items-center gap-3 animate-shake">
                <AlertCircle className="w-6 h-6 text-red-500" />
                <span className="text-red-700 font-medium">{error}</span>
              </div>
            )}

            {file && (
              <div className="space-y-6">
                {/* Range Selection */}
                <div className="bg-gradient-to-br from-purple-50 to-indigo-50 rounded-2xl p-8 border border-purple-200/50 shadow-lg">
                  <div className="flex items-center gap-3 mb-6">
                    <Scissors className="w-6 h-6 text-purple-500" />
                    <h3 className="text-xl font-bold text-gray-800">Range Selection</h3>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-6 mb-6">
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">
                        Start Page
                      </label>
                      <input
                        type="number"
                        min="1"
                        max={numPages || undefined} 
                        value={startPage}
                        onChange={handleStartPageChange}
                        className="w-full px-4 py-3 border-2 border-purple-300 rounded-xl"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">
                        End Page
                      </label>
                      <input
                        type="number"
                        min={startPage}
                        max={numPages || undefined}
                        value={endPage}
                        onChange={handleEndPageChange}
                        className="w-full px-4 py-3 border-2 border-purple-300 rounded-xl"
                      />
                    </div>
                  </div>

                  <div className="flex gap-3 mb-8">
                    <button
                      onClick={() => {setStartPage(1); setEndPage(numPages || 1);}}
                      className="flex-1 px-4 py-3 bg-gray-300 rounded-xl"
                    >
                      All Pages
                    </button>
                    <button
                      onClick={resetSelection}
                      className="flex-1 px-4 py-3 bg-red-300 rounded-xl"
                    >
                      Reset
                    </button>
                  </div>

                  <button
                    onClick={extractText}
                    disabled={loading}
                    className="w-full py-4 bg-purple-600 text-white rounded-xl font-bold"
                  >
                    {loading ? 'Extracting...' : `Extract Text (Pages ${startPage}-${endPage})`}
                  </button>
                </div>

                {extractedText && (
                  <div className="bg-green-50 rounded-2xl p-8 border border-green-200/50 shadow-lg">
                    <div className="flex items-center justify-between mb-6">
                      <div className="flex items-center gap-3">
                        <FileText className="w-6 h-6 text-green-500" />
                        <h3 className="text-xl font-bold text-gray-800">Extracted Text</h3>
                      </div>
                      <div className="flex gap-3">
                        <button onClick={generateInsights} disabled={insightsLoading} className="px-6 py-3 bg-purple-500 text-white rounded-xl">
                          {insightsLoading ? 'Analyzing...' : 'Generate Insights'}
                        </button>
                        <button onClick={downloadText} className="px-6 py-3 bg-green-500 text-white rounded-xl">
                          Download
                        </button>
                      </div>
                    </div>
                    <div className="bg-white border-2 border-green-200 rounded-xl p-6 max-h-96 overflow-y-auto">
                      <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono leading-relaxed">
                        {extractedText}
                      </pre>
                    </div>
                  </div>
                )}

                {insights && (
                  <div className="bg-purple-50 rounded-2xl p-8 border border-purple-200/50 shadow-lg">
                    <div className="flex items-center justify-between mb-6">
                      <div className="flex items-center gap-3">
                        <Brain className="w-6 h-6 text-purple-500" />
                        <h3 className="text-xl font-bold text-gray-800">AI Insights</h3>
                      </div>
                      <button onClick={downloadInsights} className="px-6 py-3 bg-purple-500 text-white rounded-xl">
                        Download Insights
                      </button>
                    </div>
                    <div className="bg-white border-2 border-purple-200 rounded-xl p-6 max-h-96 overflow-y-auto">
                      <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                        {insights}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PDFRangeExtractor;
