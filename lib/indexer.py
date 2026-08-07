from sentence_transformers import SentenceTransformer
from typing import List, Optional, Dict, Any
import numpy as np
from sqlmodel import Session, select
import asyncio
import httpx
import os
import json
import re
from db.schema import Conversation, Response, Topic, AIAnalysis, MetricEvent, UserFeedback
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class MemoryIndexer:
    def __init__(self, db_engine):
        self.engine = db_engine
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.laguna_model_endpoint = os.getenv("LAGUNA_API_ENDPOINT", "http://localhost:8080/v1")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        
    def generate_embeddings(self, text: str) -> List[float]:
        embeddings = self.embedding_model.encode([text])
        return embeddings[0].tolist()
    
    async def index_conversation(self, reddit_data: Dict[str, Any]) -> int:
        conv = Conversation(**reddit_data)
        conv.embeddings = self.generate_embeddings(reddit_data['content'])
        
        with Session(self.engine) as session:
            session.add(conv)
            session.commit()
            session.refresh(conv)
            
            asyncio.create_task(self.analyze_conversation(conv.id))
            return conv.id
    
    async def analyze_conversation(self, conversation_id: int) -> AIAnalysis:
        with Session(self.engine) as session:
            conv = session.get(Conversation, conversation_id)
            if not conv:
                raise ValueError("Conversation not found")
            
            prompt = f"""
            Analyze this Reddit conversation and provide structured insights:
            1. Summary (2-3 sentences)
            2. Key points (list of strings)
            3. Tone analysis (formal/casual, positive/negative/neutral)
            4. Engagement tips for responding (list of strings)
            
            Title: {conv.title}
            Content: {conv.content[:2000]}
            Subreddit: {conv.subreddit}
            """

            response_data = await self._call_laguna_model(prompt)
            parsed = self._parse_analysis(response_data)
            
            analysis = AIAnalysis(
                conversation_id=conversation_id,
                **parsed
            )
            
            session.add(analysis)
            session.commit()
            session.refresh(analysis)
            return analysis
    
    async def _call_laguna_model(self, prompt: str, model: str = "laguna-s-2.1-free") -> str:
        headers = {"Content-Type": "application/json"}
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.7
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.laguna_model_endpoint}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=60.0
                )
                result = response.json()
                return result["choices"][0]["message"]["content"]
            except Exception:
                return await self._call_openai_fallback(prompt)
    
    async def _call_openai_fallback(self, prompt: str) -> str:
        if not self.openai_key:
            return "Fallback response unavailable"
            
        headers = {"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"}
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30.0
            )
            result = response.json()
            return result["choices"][0]["message"]["content"]
    
    def _parse_analysis(self, content: str) -> Dict[str, Any]:
        lines = content.strip().split('\n')
        parsed = {
            "summary": "",
            "key_points": [],
            "tone_analysis": "",
            "engagement_tips": []
        }
        
        current_field = None
        buffer = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('1.') or line.startswith('2.') or line.startswith('3.') or line.startswith('4.'):
                if current_field and buffer:
                    value = ' '.join(buffer).strip()
                    if current_field in ['key_points', 'engagement_tips']:
                        parsed[current_field] = [item.strip() for item in re.findall(r'[•\-\d*]\s*(.+)', value)]
                    else:
                        parsed[current_field] = value
                buffer = []
                current_field = {
                    '1.': 'summary',
                    '2.': 'key_points',
                    '3.': 'tone_analysis',
                    '4.': 'engagement_tips'
                }.get(line[:2])
            else:
                buffer.append(line)
        
        if current_field and buffer:
            value = ' '.join(buffer).strip()
            if current_field in ['key_points', 'engagement_tips']:
                parsed[current_field] = [item.strip() for item in re.findall(r'[•\-\d*]\s*(.+)', value)]
            else:
                parsed[current_field] = value
        
        similar_responses = []
        return {**parsed, "similar_past_responses": similar_responses}
    
    async def generate_response_suggestion(self, post_content: str, subreddit: str, model: str = "laguna-s-2.1-free") -> Dict[str, Any]:
        similar = self.find_similar_responses(post_content, limit=5)
        similar_context = "\n---\n".join([
            f"Response: {r['content']}\nScore: {r['score']}" 
            for r in similar[:3]
        ]) if similar else "No similar responses found."
        
        prompt = f"""
        You are my Reddit engagement bot. Generate authentic, high-value responses to help me build karma and authority.
        
        Subreddit: r/{subreddit}
        Post content: {post_content[:1500]}
        
        Here are my previous similar responses for style reference:
        {similar_context}
        
        Generate 3 response options with different tones:
        1. Direct/Practical
        2. Story/Humorous
        3. Insightful/Analytical
        
        For each: provide the response text, expected karma range, and why it would work.
        """
        
        result = await self._call_laguna_model(prompt, model)
        suggestions = self._parse_response_suggestions(result)
        suggestions['similar_context'] = similar[:3]
        
        return suggestions
    
    def _parse_response_suggestions(self, content: str) -> Dict[str, Any]:
        return {"raw": content, "options": []}
    
    def find_similar_responses(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        query_embedding = self.embedding_model.encode([query])
        
        with Session(self.engine) as session:
            stmt = select(Response).where(Response.embeddings.is_not(None))
            responses = session.exec(stmt).all()
            
            if not responses:
                return []
            
            similarities = []
            for r in responses:
                if r.embeddings:
                    sim = cosine_similarity(
                        [query_embedding[0]], 
                        [r.embeddings[:384]]
                    )[0][0]
                    similarities.append((r, sim))
            
            similarities.sort(key=lambda x: x[1], reverse=True)
            top_responses = similarities[:limit]
            
            return [{
                "id": r.id,
                "content": r.content,
                "score": r.score,
                "topic": r.topic.name if r.topic else None,
                "similarity": round(float(sim), 4)
            } for r, sim in top_responses]
    
    async def index_response(self, response_data: Dict[str, Any]) -> int:
        response = Response(**response_data)
        response.embeddings = self.generate_embeddings(response_data['content'])
        
        with Session(self.engine) as session:
            session.add(response)
            session.commit()
            session.refresh(response)
            return response.id
    
    async def update_response_performance(self, response_id: int, karma_change: int, engagement_reaction: str = None):
        with Session(self.engine) as session:
            resp = session.get(Response, response_id)
            if not resp:
                raise ValueError("Response not found")
            
            if resp.score is None:
                resp.score = 0
            resp.score += karma_change
            resp.performance_rating = min(10.0, max(1.0, resp.score / 10.0))
            
            metric = MetricEvent(
                event_type="karma_gained" if karma_change > 0 else "karma_lost",
                value=karma_change,
                related_response_id=response_id
            )
            session.add(metric)
            session.commit()
    
    async def submit_feedback(self, response_id: int, rating: int, feedback_text: Optional[str] = None):
        with Session(self.engine) as session:
            feedback = UserFeedback(
                response_id=response_id,
                rating=rating,
                feedback_text=feedback_text
            )
            session.add(feedback)
            session.commit()
            session.refresh(feedback)
            return feedback.id
    
    def cluster_topics(self):
        with Session(self.engine) as session:
            stmt = select(Conversation).where(Conversation.embeddings.is_not(None))
            conversations = session.exec(stmt).all()
            
            if len(conversations) < 2:
                return
            
            embeddings = np.array([c.embeddings[:384] for c in conversations])
            
            clustering = DBSCAN(eps=0.5, min_samples=2, metric='cosine')
            labels = clustering.fit_predict(embeddings)
            
            topic_map = {}
            for i, label in enumerate(labels):
                if label not in topic_map:
                    topic_map[label] = []
                topic_map[label].append(conversations[i])
            
            for label, convs in topic_map.items():
                if label == -1:
                    continue
                    
                existing_topic = session.exec(
                    select(Topic).where(Topic.id == f"topic_{label}")
                ).first()
                
                if not existing_topic:
                    vectorizer = TfidfVectorizer(max_features=10, stop_words='english')
                    tfidf_matrix = vectorizer.fit_transform([c.content for c in convs])
                    feature_names = vectorizer.get_feature_names_out()
                    topic_name = " ".join(feature_names[:3])
                    
                    topic = Topic(name=topic_name, description=f"Auto-clustered from {len(convs)} conversations")
                    session.add(topic)
                    session.commit()
                    
                    for conv in convs:
                        conv.topic_id = topic.id
                    session.commit()
    
    async def get_dashboard_metrics(self) -> Dict[str, Any]:
        with Session(self.engine) as session:
            total_karma = session.exec(
                select(MetricEvent).where(MetricEvent.event_type == "karma_gained")
            ).all()
            
            conv_count = session.exec(select(Conversation)).all()
            resp_count = session.exec(select(Response)).all()
            
            return {
                "total_conversations": len(conv_count),
                "total_responses": len(resp_count),
                "total_karma_events": len(total_karma),
                "recent_analyses": len(session.exec(select(AIAnalysis)).all())
            }

def get_indexer(db_engine) -> MemoryIndexer:
    return MemoryIndexer(db_engine)
