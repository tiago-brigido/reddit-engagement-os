from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, create_engine, Session, select
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import asyncio
import os

from lib.indexer import MemoryIndexer

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./reddit_os.db")
engine = create_engine(DATABASE_URL, echo=False)

indexer: MemoryIndexer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global indexer
    indexer = MemoryIndexer(DATABASE_URL)
    yield

app = FastAPI(title="Reddit Engagement OS API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConversationPayload(BaseModel):
    reddit_id: str
    subreddit: str
    title: str
    post_url: str
    content: str
    author: str
    score: int = 0
    num_comments: int = 0
    created_utc: Optional[str] = None
    permalink: str = ""
    flair: Optional[str] = None

class ResponsePayload(BaseModel):
    conversation_id: Optional[int] = None
    content: str
    score: Optional[int] = None

class FeedbackPayload(BaseModel):
    response_id: int
    rating: int
    feedback_text: Optional[str] = None

class PerformancePayload(BaseModel):
    karma_change: int
    engagement_reaction: Optional[str] = None

@app.get("/health")
async def health_check():
    return {"status": "ok", "ai_engine": "laguna-s-2.1-free" if indexer else "initializing"}

@app.post("/conversations/index")
async def index_conversation(conv_data: ConversationPayload):
    conv_dict = conv_data.model_dump()
    conv_dict['created_utc'] = conv_dict.get('created_utc') or datetime.utcnow().isoformat()
    
    with Session(engine) as session:
        from db.schema import Conversation
        conv = Conversation(**conv_dict)
        conv.created_at = datetime.utcnow().isoformat()
        from lib.indexer import MemoryIndexer as MI
        conv.embeddings = conv.embeddings  # Let indexer handle embeddings
        session.add(conv)
        session.commit()
        session.refresh(conv)
        asyncio.create_task(indexer.analyze_conversation(conv.id))
    return {"id": conv.id, "message": "Conversation indexed. Analysis started in background."}

@app.get("/responses/similar")
async def get_similar_responses(query: str, limit: int = 5):
    results = indexer.find_similar_responses(query, limit)
    return {"results": results}

@app.post("/responses/generate")
async def generate_response(post_content: str, subreddit: str, model: str = "laguna-s-2.1-free"):
    suggestion = await indexer.generate_response_suggestion(post_content, subreddit, model)
    return suggestion

@app.post("/responses/index")
async def index_response(resp_data: ResponsePayload):
    resp_dict = resp_data.model_dump()
    resp_id = await indexer.index_response(resp_dict)
    return {"id": resp_id, "message": "Response indexed successfully"}

@app.post("/responses/{response_id}/performance")
async def update_performance(response_id: int, payload: PerformancePayload):
    await indexer.update_response_performance(response_id, payload.karma_change, payload.engagement_reaction)
    return {"status": "updated", "response_id": response_id}

@app.post("/feedback")
async def submit_feedback(payload: FeedbackPayload):
    feedback_id = await indexer.submit_feedback(payload.response_id, payload.rating, payload.feedback_text)
    return {"feedback_id": feedback_id, "status": "recorded"}

@app.get("/metrics/dashboard")
async def get_dashboard_metrics():
    return await indexer.get_dashboard_metrics()

@app.get("/topics/trending")
async def get_trending_topics(limit: int = 10):
    with Session(engine) as session:
        from db.schema import Topic
        stmt = select(Topic).order_by(Topic.conversation_count.desc()).limit(limit)
        topics = session.exec(stmt).all()
        return [{"name": t.name, "description": t.description, "count": t.conversation_count} for t in topics]

@app.post("/topics/cluster")
async def trigger_clustering():
    indexer.cluster_topics()
    return {"status": "clustering complete"}

@app.get("/responses/{response_id}")
async def get_response(response_id: int):
    with Session(engine) as session:
        from db.schema import Response
        resp = session.get(Response, response_id)
        if not resp:
            raise HTTPException(status_code=404, detail="Response not found")
        return {"id": resp.id, "content": resp.content, "score": resp.score}
