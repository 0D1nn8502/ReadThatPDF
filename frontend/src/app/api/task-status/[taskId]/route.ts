import { NextRequest, NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";

const BACKEND_API_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: { taskId: string } }
) {
  try {
    const { userId } = await auth();
    
    if (!userId) {
      return NextResponse.json(
        { error: 'Authentication required' },
        { status: 401 }
      );
    }

    const { taskId } = params;

    const response = await fetch(`${BACKEND_API_URL}/task-status/${taskId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Backend API error: ${response.status}`);
    }

    const result = await response.json();
    return NextResponse.json(result);

  } catch (error) {
    console.error('Error fetching task status:', error);
    const errorMessage = error instanceof Error ? error.message : 'Failed to fetch task status';
    return NextResponse.json(
      { error: errorMessage },
      { status: 500 }
    );
  }
}