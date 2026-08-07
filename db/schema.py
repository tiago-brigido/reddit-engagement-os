from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
import json

class ConversationBase(SQLModel):
    reddit_id: str = Field(index=True)
    subreddit: str = Field(index=True)
    title: str
    post_url: str
    content: str
    author: str
    score: int = 0
    num_comments: int = 0
    created_utc: str = ""
    permalink: str = ""
    flair: Optional[str] = None

class Conversation(ConversationBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    embeddings: Optional[str] = None
    topic_id: Optional[int] = Field(default=None, foreign_key="topic.id")
    created_at: str = ""

class ResponseBase(SQLModel):
    conversation_id: Optional[int] = None
    content: str
    score: Optional[int] = None
    author_karma_at_response: Optional[int] = None
    response_time_minutes: Optional[float] = None
    ai_generated: bool = False
    model_used: Optional[str] = None
    performance_rating: Optional[float] = None

class Response(ResponseBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    embeddings: Optional[str] = None
    topic_id: Optional[int] = Field(default=None, foreign_key="topic.id")
    created_at: str = ""

class Topic(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    embedding: Optional[str] = None
    conversation_count: int = 0
    response_pattern: Optional[str] = None

class MetricEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    event_type: str
    value: float
    timestamp: str = ""
    related_response_id: Optional[int] = None
    meta_data: Optional[str] = None

class AIAnalysis(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int
    summary: str
    key_points: str
    tone_analysis: str
    engagement_tips: str
    similar_past_responses: str
    created_at: str = ""

class UserFeedback(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    response_id: int
    rating: int
    feedback_text: Optional[str] = None
    created_at: str = ""
