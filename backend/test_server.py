#!/usr/bin/env python3

# Simple test server to check if basic FastAPI works
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Test PDF Processing API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Test server is running!"}

@app.get("/health")
async def health():
    return {"status": "healthy", "message": "Basic server is working"}

if __name__ == "__main__":
    print("🚀 Starting test server...")
    uvicorn.run(
        "test_server:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True
    )