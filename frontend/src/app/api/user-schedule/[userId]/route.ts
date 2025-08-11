import { NextRequest, NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";

const BACKEND_API_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: { userId: string } }
) {
  try {
    const { userId: authUserId } = await auth();
    
    if (!authUserId) {
      return NextResponse.json(
        { error: 'Authentication required' },
        { status: 401 }
      );
    }

    const { userId } = params;

    // Ensure users can only access their own schedule
    if (authUserId !== userId) {
      return NextResponse.json(
        { error: 'Unauthorized access' },
        { status: 403 }
      );
    }

    const response = await fetch(`${BACKEND_API_URL}/user-schedule/${userId}`, {
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
    console.error('Error fetching user schedule:', error);
    const errorMessage = error instanceof Error ? error.message : 'Failed to fetch user schedule';
    return NextResponse.json(
      { error: errorMessage },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { userId: string } }
) {
  try {
    const { userId: authUserId } = await auth();
    
    if (!authUserId) {
      return NextResponse.json(
        { error: 'Authentication required' },
        { status: 401 }
      );
    }

    const { userId } = params;

    // Ensure users can only cancel their own schedule
    if (authUserId !== userId) {
      return NextResponse.json(
        { error: 'Unauthorized access' },
        { status: 403 }
      );
    }

    const response = await fetch(`${BACKEND_API_URL}/user-schedule/${userId}`, {
      method: 'DELETE',
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
    console.error('Error cancelling user schedule:', error);
    const errorMessage = error instanceof Error ? error.message : 'Failed to cancel schedule';
    return NextResponse.json(
      { error: errorMessage },
      { status: 500 }
    );
  }
}