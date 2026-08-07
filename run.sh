#!/bin/bash
# Reddit Engagement OS - Quick Start Script
echo "Starting Reddit Engagement OS..."
source venv/bin/activate
export DATABASE_URL="sqlite:///./reddit_os.db"
exec "$@"
