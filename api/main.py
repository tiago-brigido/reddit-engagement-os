from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, create_engine, Session, select
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import os

from db.schema import Conversation, Response, Topic, AIAnalysis, UserFeedback, MetricEvent
from lib.indexer import MemoryIndexer

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/reddit_os")
engine = create_engine(DATABASE_URL)

indexer: MemoryIndexer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global indexer
    SQLModel.metadata.create_all(engine)
    indexer = MemoryIndexer(engine)
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
    score: int
    num_comments: int
    created_utc: str
    permalink: str
    flair: Optional[str] = None

class ResponsePayload(BaseModel):
    conversation_id: int
    content: str
    score: Optional[int] = None

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/conversations/index")
async def index_conversation(conv_data: ConversationPayload):
    conv_dict = conv_data.model_dump()
    from datetime import datetime
    conv_dict['created_utc'] = datetime.fromisoformat(conv_dict['created_utc'].replace('Z', '+00:00')) if conv_dict['created_utc'] else datetime.utcnow()
    
    conv = Conversation(**conv_dict)
    conv.embeddings = indexer.generate_embeddings(conv_data.content)
    
    with Session(engine) as session:
        session.add(conv)
        session.commit()
        session.refresh(conv)
        asyncio.create_task(indexer.analyze_conversation(conv.id))
    return {"id": conv.id}

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
    resp = Response(**resp_dict)
    resp.embeddings = indexer.generate_embeddings(resp_dict['content'])
    
    with Session(engine) as session:
        session.add(resp)
        session.commit()
        session.refresh(resp)
    return {"id": resp.id}

@app.post("/responses/{response_id}/performance")
async def update_performance(response_id: int, karma_change: int, engagement_reaction: Optional[str] = None):
    await indexer.update_response_performance(response_id, karma_change, engagement_reaction)
    return {"status": "updated"}

@app.post("/feedback")
async def submit_feedback(response_id: int, rating: int, feedback_text: Optional[str] = None):
    feedback_id = await indexer.submit_feedback(response_id, rating, feedback_text)
    return {"feedback_id": feedback_id}

@app.get("/metrics/dashboard")
async def get_dashboard_metrics():
    return await indexer.get_dashboard_metrics()

@app.get("/topics/trending")
async def get_trending_topics(limit: int = 10):
    with Session(engine) as session:
        stmt = select(Topic).order_by(Topic.conversation_count.desc()).limit(limit)
        topics = session.exec(stmt).all()
        return [{"name": t.name, "description": t.description, "count": t.conversation_count} for t in topics]

@app.post("/topics/cluster")
async def trigger_clustering():
    indexer.cluster_topics()
    return {"status": "clustering complete"}
