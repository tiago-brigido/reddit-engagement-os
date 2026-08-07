from sentence_transformers import SentenceTransformer
from typing import List, Optional, Dict, Any
import numpy as np
from sqlmodel import SQLModel, create_engine, Session, select
import asyncio
import httpx
import os
import json
import re
from datetime import datetime
from db.schema import Conversation, Response, Topic, AIAnalysis, MetricEvent, UserFeedback
from sklearn.cluster import DBSCAN

class MemoryIndexer:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url, echo=False)
        SQLModel.metadata.create_all(self.engine)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.laguna_model_endpoint = os.getenv("LAGUNA_API_ENDPOINT", "http://localhost:8080/v1")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        
    def _serialize_embedding(self, embedding: List[float]) -> str:
        return json.dumps(embedding)
    
    def _deserialize_embedding(self, embedding_str: Optional[str]) -> Optional[List[float]]:
        if embedding_str is None:
            return None
        try:
            return json.loads(embedding_str)
        except:
            return None
    
    def generate_embeddings(self, text: str) -> List[float]:
        embeddings = self.embedding_model.encode([text])
        return embeddings[0].tolist()
    
    async def index_conversation(self, reddit_data: Dict[str, Any]) -> int:
        conv = Conversation(**reddit_data)
        conv.created_utc = reddit_data.get('created_utc', datetime.utcnow().isoformat())
        conv.created_at = datetime.utcnow().isoformat()
        conv.embeddings = self._serialize_embedding(self.generate_embeddings(reddit_data.get('content', '') + ' ' + reddit_data.get('title', '')))
        
        with Session(self.engine) as session:
            session.add(conv)
            session.commit()
            session.refresh(conv)
            asyncio.create_task(self.analyze_conversation(conv.id))
            return conv.id
    
    async def analyze_conversation(self, conversation_id: int):
        with Session(self.engine) as session:
            conv = session.get(Conversation, conversation_id)
            if not conv:
                return
            
            content = conv.content or ''
            title = conv.title or ''
            subreddit = conv.subreddit or ''
            
            prompt = f"""
            Analyze this Reddit conversation and provide structured insights.

            Title: {title}
            Content: {content[:2000]}
            Subreddit: {subreddit}

            Provide your response in this exact format:
            SUMMARY: [2-3 sentence summary]
            
            KEY_POINTS:
            - point 1
            - point 2
            - point 3
            
            TONE: [formal/casual, positive/negative/neutral]
            
            ENGAGEMENT_TIPS:
            - tip 1
            - tip 2
"""
            
            try:
                result = await self._call_laguna_model(prompt)
                parsed = self._parse_analysis(result)
                
                analysis = AIAnalysis(
                    conversation_id=conversation_id,
                    summary=parsed.get('summary', ''),
                    key_points='\n'.join(parsed.get('key_points', [])),
                    tone_analysis=parsed.get('tone_analysis', ''),
                    engagement_tips='\n'.join(parsed.get('engagement_tips', [])),
                    similar_past_responses=json.dumps(parsed.get('similar_past_responses', []))
                )
                
                session.add(analysis)
                session.commit()
            except Exception as e:
                print(f"Analysis failed for conv {conversation_id}: {e}")
    
    async def _call_laguna_model(self, prompt: str, model: str = "laguna-s-2.1-free") -> str:
        headers = {"Content-Type": "application/json"}
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.7,
            "stream": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.laguna_model_endpoint}/chat/completions",
                    headers=headers,
                    json=data
                )
                result = response.json()
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"Laguna API call failed: {e}")
            return self._generate_local_response(prompt)
    
    def _generate_local_response(self, prompt: str) -> str:
        from datetime import datetime
        
        if 'SUMMARY:' in prompt and 'KEY_POINTS' in prompt:
            return f"""
SUMMARY: {prompt[:100]}... This post discusses key strategies and experiences that can help others in similar situations.

KEY_POINTS:
- Authentic experience sharing
- Practical actionable advice
- Community value provision

TONE: casual, helpful, experienced

ENGAGEMENT_TIPS:
- Start with empathy for their situation
- Share specific numbers or results
- Offer a concrete action they can take today
"""
        
        if 'Generate 3 response options' in prompt:
            return json.dumps([
                {
                    "tone": "Direct/Practical",
                    "content": "Here's what worked for me: focus on providing genuine value first, then the backlinks and karma naturally follow. I recommend starting with 3-5 highly specific comments per day in relevant subreddits rather than broad posting.",
                    "expected_karma": "10-50",
                    "reason": "Direct, actionable advice that others can immediately apply"
                },
                {
                    "tone": "Story/Humorous",
                    "content": "I once spent an entire weekend crafting what I thought was genius content, only to realize I'd been posting in the wrong subreddits. Lesson learned: match your expertise to the audience. What specific niche are you targeting?",
                    "expected_karma": "20-100",
                    "reason": "Relatable failure story that invites engagement and shows humility"
                },
                {
                    "tone": "Insightful/Analytical",
                    "content": "The most effective Reddit strategy combines consistent daily engagement with strategic cross-linking. Think of it as building a content flywheel: each valuable comment drives karma, which builds credibility for your profile, which amplifies future posts.",
                    "expected_karma": "15-75",
                    "reason": "Framework-based approach that demonstrates expertise while positioning you as an authority"
                }
            ])
        
        return f"Response generated at {datetime.utcnow().isoformat()}"
    
    def _parse_analysis(self, content: str) -> Dict[str, Any]:
        parsed = {
            "summary": "",
            "key_points": [],
            "tone_analysis": "",
            "engagement_tips": [],
            "similar_past_responses": []
        }
        
        sections = content.split('\n\n')
        for section in sections:
            lines = section.strip().split('\n')
            header = lines[0].strip().upper()
            
            if 'SUMMARY' in header:
                parsed["summary"] = ' '.join(lines[1:]).strip()
            elif 'KEY_POINTS' in header:
                for line in lines[1:]:
                    line = line.strip()
                    if line.startswith('- ') or line.startswith('• '):
                        parsed["key_points"].append(line[2:])
            elif 'TONE' in header:
                parsed["tone_analysis"] = ' '.join(lines[1:]).strip()
            elif 'ENGAGEMENT_TIPS' in header:
                for line in lines[1:]:
                    line = line.strip()
                    if line.startswith('- ') or line.startswith('• '):
                        parsed["engagement_tips"].append(line[2:])
        
        return parsed
    
    async def generate_response_suggestion(self, post_content: str, subreddit: str, model: str = "laguna-s-2.1-free") -> Dict[str, Any]:
        similar = self.find_similar_responses(post_content, limit=5)
        similar_context = "\n---\n".join([
            f"Response: {r['content']}\nScore: {r['score']}" 
            for r in similar[:3]
        ]) if similar else "No similar responses found."
        
        prompt = f"""
        You are my Reddit engagement assistant. Generate authentic, high-value responses to help me build karma and authority.

        Subreddit: r/{subreddit}
        Post content: {post_content[:1500]}

        Here are my previous similar responses for style reference:
        {similar_context}

        Generate 3 response options with different tones:
        1. Direct/Practical
        2. Story/Humorous  
        3. Insightful/Analytical

        Format: JSON array with objects containing 'tone', 'content', 'expected_karma', 'reason'.
"""
        
        try:
            result = await self._call_laguna_model(prompt, model)
            suggestions = self._parse_response_suggestions(result)
        except:
            suggestions = {"options": [], "error": "Failed to generate suggestions"}
        
        return {
            "suggestions": suggestions.get('options', []),
            "similar_context": similar[:3]
        }
    
    def _parse_response_suggestions(self, content: str) -> Dict[str, Any]:
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return {"options": data}
            return {"options": data.get('responses', [])}
        except json.JSONDecodeError:
            return {"options": [{"raw": content}]}
    
    def find_similar_responses(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        query_embedding = self.embedding_model.encode([query])
        
        with Session(self.engine) as session:
            stmt = select(Response).where(Response.embeddings.isnot(None))
            responses = session.exec(stmt).all()
            
            if not responses:
                return []
            
            similarities = []
            for r in responses:
                r_emb = self._deserialize_embedding(r.embeddings)
                if r_emb:
                    from sklearn.metrics.pairwise import cosine_similarity
                    sim = cosine_similarity(
                        [query_embedding[0][:min(len(query_embedding[0]), len(r_emb))]], 
                        [r_emb[:min(len(query_embedding[0]), len(r_emb))]]
                    )[0][0]
                    similarities.append((r, sim))
            
            similarities.sort(key=lambda x: x[1], reverse=True)
            top_responses = similarities[:limit]
            
            return [{
                "id": r.id,
                "content": r.content,
                "score": r.score,
                "author": r.author,
                "topic": None,
                "similarity": round(float(sim), 4)
            } for r, sim in top_responses]
    
    def find_responses_by_author(self, author: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find all responses by a specific author/nickname"""
        with Session(self.engine) as session:
            stmt = select(Response).where(
                Response.author.contains(author) if Response.author else False
            ).order_by(Response.created_at.desc()).limit(limit)
            responses = session.exec(stmt).all()
            
            return [{
                "id": r.id,
                "content": r.content,
                "score": r.score,
                "author": r.author,
                "created_at": r.created_at,
                "ai_generated": r.ai_generated,
                "model_used": r.model_used
            } for r in responses]
    
    def search_responses_by_content(self, query: str, author: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search responses by content similarity, optionally filtered by author"""
        query_embedding = self.embedding_model.encode([query])
        
        with Session(self.engine) as session:
            stmt = select(Response).where(Response.embeddings.isnot(None))
            if author:
                stmt = stmt.where(Response.author == author)
            responses = session.exec(stmt).all()
            
            similarities = []
            for r in responses:
                r_emb = self._deserialize_embedding(r.embeddings)
                if r_emb:
                    from sklearn.metrics.pairwise import cosine_similarity
                    sim = cosine_similarity(
                        [query_embedding[0][:min(len(query_embedding[0]), len(r_emb))]], 
                        [r_emb[:min(len(query_embedding[0]), len(r_emb))]]
                    )[0][0]
                    similarities.append((r, sim))
            
            similarities.sort(key=lambda x: x[1], reverse=True)
            top_responses = similarities[:limit]
            
            return [{
                "id": r.id,
                "content": r.content,
                "score": r.score,
                "author": r.author,
                "similarity": round(float(sim), 4),
                "model_used": r.model_used
            } for r, sim in top_responses]
    
    async def index_response(self, response_data: Dict[str, Any]) -> int:
        resp_data = response_data.copy()
        resp_data.setdefault('created_at', datetime.utcnow().isoformat())
        resp_data.setdefault('created_at', '')
        resp = Response(**resp_data)
        resp.embeddings = self._serialize_embedding(self.generate_embeddings(resp_data.get('content', '')))
        
        with Session(self.engine) as session:
            session.add(resp)
            session.commit()
            session.refresh(resp)
            return resp.id
    
    async def update_response_performance(self, response_id: int, karma_change: int, engagement_reaction: Optional[str] = None):
        with Session(self.engine) as session:
            resp = session.get(Response, response_id)
            if not resp:
                return
            
            resp.score = (resp.score or 0) + karma_change
            resp.performance_rating = min(10.0, max(1.0, (resp.score or 0) / 10.0))
            
            metric = MetricEvent(
                event_type="karma_gained" if karma_change > 0 else "karma_lost",
                value=karma_change,
                timestamp=datetime.utcnow().isoformat(),
                related_response_id=response_id
            )
            session.add(metric)
            session.commit()
    
    async def submit_feedback(self, response_id: int, rating: int, feedback_text: Optional[str] = None):
        with Session(self.engine) as session:
            feedback = UserFeedback(
                response_id=response_id,
                rating=rating,
                feedback_text=feedback_text,
                created_at=datetime.utcnow().isoformat()
            )
            session.add(feedback)
            session.commit()
            return feedback.id
    
    def cluster_topics(self):
        with Session(self.engine) as session:
            stmt = select(Conversation).where(Conversation.embeddings.isnot(None))
            conversations = session.exec(stmt).all()
            
            if len(conversations) < 2:
                return
            
            embeddings = []
            valid_convs = []
            for c in conversations:
                emb = self._deserialize_embedding(c.embeddings)
                if emb:
                    embeddings.append(emb[:384])
                    valid_convs.append(c)
            
            if len(embeddings) < 2:
                return
            
            embeddings = np.array(embeddings)
            clustering = DBSCAN(eps=0.5, min_samples=2, metric='cosine')
            labels = clustering.fit_predict(embeddings)
            
            topic_map = {}
            for i, label in enumerate(labels):
                if label not in topic_map:
                    topic_map[label] = []
                topic_map[label].append(valid_convs[i])
            
            for label, convs in topic_map.items():
                if label == -1:
                    continue
                
                existing_topic = session.get(Topic, f"topic_{label}")
                if existing_topic:
                    existing_topic.conversation_count += len(convs)
                else:
                    from sklearn.feature_extraction.text import TfidfVectorizer
                    vectorizer = TfidfVectorizer(max_features=5, stop_words='english')
                    try:
                        tfidf_matrix = vectorizer.fit_transform([c.title or c.content or '' for c in convs])
                        feature_names = vectorizer.get_feature_names_out()
                        topic_name = " ".join(feature_names[:3])
                    except:
                        topic_name = f"topic_{label}"
                    
                    topic = Topic(name=topic_name, description=f"Auto-clustered from {len(convs)} conversations")
                    session.add(topic)
                    session.commit()
                    
                    for conv in convs:
                        conv.topic_id = topic.id
                    session.commit()
    
    async def get_dashboard_metrics(self) -> Dict[str, Any]:
        with Session(self.engine) as session:
            total_conversations = len(session.exec(select(Conversation)).all())
            total_responses = len(session.exec(select(Response)).all())
            karma_events = session.exec(select(MetricEvent).where(MetricEvent.event_type == "karma_gained")).all()
            total_karma = sum(e.value for e in karma_events)
            
            return {
                "total_conversations": total_conversations,
                "total_responses": total_responses,
                "total_karma_events": len(karma_events),
                "total_karma_gain": total_karma
            }
