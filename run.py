#!/usr/bin/env python3
"""
Tesseracts World API Startup Script

This script initializes and runs the Tesseracts World API server.
"""

import uvicorn
import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config.settings import settings

def main():
    """Main entry point for the Tesseracts World API"""
    
    print("🌍 Starting Tesseracts World - The Universal API for Movement")
    print("=" * 60)
    print(f"Version: {settings.app_version}")
    print(f"Host: {settings.api_host}:{settings.api_port}")
    print(f"Debug: {settings.debug}")
    print("=" * 60)
    
    # Run the FastAPI application
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )

if __name__ == "__main__":
    main()
