import { NextRequest, NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { createClerkClient } from "@clerk/nextjs/server";

// Initialize Clerk client
const clerkClient = createClerkClient({
  secretKey: process.env.CLERK_SECRET_KEY,
});

// Backend API URL
const BACKEND_API_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';

// TypeScript interfaces
interface ProcessPDFRequest {
  text: string;
  processing_mode: 'immediate_only' | 'schedule_only' | 'immediate_and_schedule';
  immediate_chunks_count: number;
  chunks_per_delivery: number;
  schedule_type: 'daily' | 'weekly' | 'custom';
  schedule_time: string;
  user_timezone: string;
  custom_interval_hours?: number;
}

interface BackendPayload {
  text: string;
  userId: string;
  email: string;
  processing_mode: string;
  immediate_chunks_count: number;
  chunks_per_delivery: number;
  schedule_type: string;
  schedule_time: string;
  user_timezone: string;
}

interface BackendResponse {
  status: string;
  total_chunks: number;
  chunks_processed_immediately: number;
  schedule_set: boolean;
  immediate_task_id: string | null;
}

export async function POST(request: NextRequest) {
    try {
        // Check authentication
        const { userId } = await auth();
        console.log("User ID: ", userId); 
        
        if (!userId) {
            return NextResponse.json(
                { error: 'Authentication needed' },
                { status: 401 }
            );
        }

        // Get user info from Clerk with error handling
        let user;
        try {
            console.log('Attempting to fetch user with ID:', userId);
            console.log('clerkClient:', typeof clerkClient, clerkClient);
            console.log('clerkClient.users:', typeof clerkClient?.users, clerkClient?.users);
            
            user = await clerkClient.users.getUser(userId);
            console.log('Successfully fetched user:', user?.id);
        } catch (clerkError) {
            console.error('Error fetching user from Clerk:', {
                error: clerkError,
                userId: userId,
                errorMessage: clerkError instanceof Error ? clerkError.message : 'Unknown error'
            });
            return NextResponse.json(
                { error: 'Failed to fetch user information' },
                { status: 500 }
            );
        }

        const email = user.primaryEmailAddress?.emailAddress;
        
        if (!email) {
            return NextResponse.json(
                { error: 'User email not found' },
                { status: 400 }
            );
        }

        const body: ProcessPDFRequest = await request.json();
        const {
            text,
            processing_mode,
            immediate_chunks_count,
            chunks_per_delivery,
            schedule_type,
            schedule_time,
            user_timezone,
            custom_interval_hours
        } = body;

        if (!text?.trim()) {
            return NextResponse.json(
                { error: 'PDF text is required' },
                { status: 400 }
            );
        }

        // Prepare payload for backend API
        const backendPayload: BackendPayload = {
            text,
            userId,
            email,
            processing_mode,
            immediate_chunks_count,
            chunks_per_delivery,
            schedule_type,
            schedule_time,
            user_timezone
        };

        console.log('Calling backend API with payload:', backendPayload);
        console.log('Original body from frontend:', body);
        console.log('Individual fields:', {
            processing_mode,
            user_timezone,
            schedule_type,
            immediate_chunks_count
        });

        // Call the FastAPI backend
        const backendResponse = await fetch(`${BACKEND_API_URL}/process-pdf-text`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(backendPayload)
        });

        if (!backendResponse.ok) {
            const errorData = await backendResponse.json().catch(() => ({}));
            console.error('Backend API error:', {
                status: backendResponse.status,
                statusText: backendResponse.statusText,
                errorData
            });
            throw new Error(errorData.detail || `Backend API error: ${backendResponse.status}`);
        }

        const result: BackendResponse = await backendResponse.json();
        console.log('Backend API response:', result);

        return NextResponse.json(result);

    } catch (error) {
        console.error('Error processing PDF text:', error);
        const errorMessage = error instanceof Error ? error.message : 'Failed to process PDF text';
        return NextResponse.json(
            { error: errorMessage },
            { status: 500 }
        );
    }
}