// Simple test to check if frontend can reach backend
const BACKEND_URL = 'http://localhost:8000';

async function testConnection() {
    try {
        console.log('Testing connection to backend...');
        
        // Test health endpoint
        const healthResponse = await fetch(`${BACKEND_URL}/health`);
        const healthData = await healthResponse.json();
        console.log('✅ Health check:', healthData);
        
        // Test user schedule endpoint (should work without auth from backend directly)
        const scheduleResponse = await fetch(`${BACKEND_URL}/user-schedule/test-user`);
        const scheduleData = await scheduleResponse.json();
        console.log('✅ Schedule check:', scheduleData);
        
        console.log('🎉 Backend connection is working!');
        
    } catch (error) {
        console.error('❌ Connection failed:', error);
    }
}

testConnection();