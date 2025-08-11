import { NextRequest, NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";

// This is a simple insights generator for the PDF range extractor
// For full processing with scheduling, use the process-pdf-text endpoint

export async function POST(request: NextRequest) {
  try {
    const { userId } = await auth();
    
    if (!userId) {
      return NextResponse.json(
        { error: 'Authentication required' },
        { status: 401 }
      );
    }

    const body = await request.json();
    const { text, pages } = body;

    if (!text?.trim()) {
      return NextResponse.json(
        { error: 'Text is required' },
        { status: 400 }
      );
    }

    // Simple insights generation (you could enhance this to call your backend's insights API)
    const wordCount = text.split(/\s+/).length;
    const charCount = text.length;
    const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0).length;
    const avgWordsPerSentence = Math.round(wordCount / sentences);

    const insights = `📊 Document Analysis for Pages ${pages}:

📝 Content Statistics:
• Word count: ${wordCount.toLocaleString()}
• Character count: ${charCount.toLocaleString()}
• Sentences: ${sentences}
• Average words per sentence: ${avgWordsPerSentence}

🔍 Key Observations:
• Document length: ${wordCount < 500 ? 'Short' : wordCount < 2000 ? 'Medium' : 'Long'}
• Reading time: ~${Math.ceil(wordCount / 200)} minutes
• Complexity: ${avgWordsPerSentence < 15 ? 'Simple' : avgWordsPerSentence < 25 ? 'Moderate' : 'Complex'}

💡 Quick Summary:
This appears to be a ${wordCount < 500 ? 'brief document or excerpt' : wordCount < 2000 ? 'standard document' : 'comprehensive document'} with ${sentences} sentences. The writing style is ${avgWordsPerSentence < 15 ? 'concise and direct' : avgWordsPerSentence < 25 ? 'moderately detailed' : 'detailed and complex'}.

Note: For advanced AI-powered insights with scheduling and email delivery, use the "Process & Schedule" tab.`;

    return NextResponse.json({ insights });

  } catch (error) {
    console.error('Error generating insights:', error);
    const errorMessage = error instanceof Error ? error.message : 'Failed to generate insights';
    return NextResponse.json(
      { error: errorMessage },
      { status: 500 }
    );
  }
}