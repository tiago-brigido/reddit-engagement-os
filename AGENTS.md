# Reddit Engagement OS - Development Guide

## Project Overview
Memory-based Reddit engagement system that helps build authentic karma and backlinks.

## Architecture
- **API:** FastAPI backend with SQLModel
- **AI Brain:** lib/indexer.py using Laguna S 2.1 Free + sentence-transformers
- **Extension:** Chrome extension for capturing Reddit posts
- **Dashboard:** Next.js frontend

## Development Commands
```bash
# Start everything with Docker
docker-compose up -d

# API only
cd api && python -m uvicorn main:app --reload

# Web dashboard
cd web && npm run dev
```

## Key Files
- `db/schema.py` - Database models
- `lib/indexer.py` - AI memory brain
- `api/main.py` - REST API endpoints
- `extension/manifest.json` - Chrome extension
- `web/pages/` - Next.js pages
