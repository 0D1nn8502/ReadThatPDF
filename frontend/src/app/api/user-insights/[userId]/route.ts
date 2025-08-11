import { NextRequest, NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server"; 

BACKEND_API_URL = process.env.BACKEND_API_URL; 


export async function GET(
    request: NextRequest,
    { params }: { params: Promise<{ userId: string }> }
) {
    const { userId } = await params;  // ✅ Await the params
    
    // Rest of your code stays the same
    const authUserId = await auth().userId;
    
    if (!authUserId) {
        return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    if (authUserId !== userId) {
        return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
    }

    try {
        const response = await fetch(`${BACKEND_API_URL}/user-insights/${userId}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error('Error fetching user insights:', error);
        return NextResponse.json(
            { error: 'Failed to fetch user insights' },
            { status: 500 }
        );
    }
}