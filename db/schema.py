from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
import sqlalchemy as sa

class ConversationBase(SQLModel):
    reddit_id: str = Field(index=True)
    subreddit: str = Field(index=True)
    title: str
    post_url: str
    content: str
    author: str
    score: int
    num_comments: int
    created_utc: datetime
    permalink: str
    flair: Optional[str] = None

class Conversation(ConversationBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    embeddings: Optional[List[float]] = Field(default=None, sa_column=sa.Column(sa.ARRAY(sa.Float)))
    topic_id: Optional[int] = Field(default=None, foreign_key="topic.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    responses: List["Response"] = Relationship(back_populates="conversation")
    topic: Optional["Topic"] = Relationship(back_populates="conversations")

class ResponseBase(SQLModel):
    conversation_id: int
    content: str
    score: Optional[int] = None
    author_karma_at_response: Optional[int] = None
    response_time_minutes: Optional[float] = None
    ai_generated: bool = False
    model_used: Optional[str] = None
    performance_rating: Optional[float] = None  # 1-10 scale

class Response(ResponseBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    embeddings: Optional[List[float]] = Field(default=None, sa_column=sa.Column(sa.ARRAY(sa.Float)))
    topic_id: Optional[int] = Field(default=None, foreign_key="topic.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    conversation: Conversation = Relationship(back_populates="responses")
    topic: Optional["Topic"] = Relationship(back_populates="responses")

class Topic(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    embedding: Optional[List[float]] = Field(default=None, sa_column=sa.Column(sa.ARRAY(sa.Float)))
    conversation_count: int = 0
    response_pattern: Optional[str] = None
    
    conversations: List[Conversation] = Relationship(back_populates="topic")
    responses: List[Response] = Relationship(back_populates="topic")

class MetricEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    event_type: str  # karma_gained, response_posted, etc
    value: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    related_response_id: Optional[int] = None
    metadata: Optional[str] = None

class AIAnalysis(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int
    summary: str
    key_points: List[str]
    tone_analysis: str
    engagement_tips: List[str]
    similar_past_responses: List[int] = Field(sa_column=sa.Column(sa.ARRAY(sa.Integer)))
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserFeedback(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    response_id: int
    rating: int  # 1-5
    feedback_text: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
