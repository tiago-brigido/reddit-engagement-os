#!/bin/bash
# Reddit Engagement OS - Quick Start Script

echo "=========================================="
echo "Reddit Engagement OS - Quick Start"
echo "=========================================="
echo ""

# Check if .env exists, create from template
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.template .env 2>/dev/null || echo "
LAGUNA_API_ENDPOINT=http://localhost:8080/v1
DATABASE_URL=sqlite:///./reddit_os.db
OPENAI_API_KEY=
" > .env
    echo ".env file created!"
fi

echo ""
echo "Configuration:"
echo "- Edit .env to add your Laguna S 2.1 Free endpoint"
echo "- Database: SQLite (reddit_os.db)"
echo ""

# Activate venv if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install fastapi uvicorn sqlmodel sentence-transformers scikit-learn numpy httpx python-dotenv rich
fi

echo ""
echo "Quick Commands:"
echo "1. Start API server:  uvicorn api.main:app --reload"
echo "2. Start CLI:        python3 CLI.py"
echo "3. Test full flow:   python3 setup_test.py"
echo ""

# Check if user wants to start the API
read -p "Start API server now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting API server on http://localhost:8000"
    uvicorn api.main:app --reload --port 8000
fi
