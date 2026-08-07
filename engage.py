#!/usr/bin/env python3
"""
Quick interface for Reddit Engagement OS
Usage: python3 engage.py "post content here" "subreddit name"
"""

import asyncio
import sys
import os

sys.path.insert(0, '/Users/tiago/reddit-engagement-os')
os.environ['DATABASE_URL'] = 'sqlite:///./reddit_os.db'

from lib.indexer import MemoryIndexer

async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 engage.py '<post content>' '<subreddit>'")
        print("Example: python3 engage.py 'How to start a SaaS?' 'Entrepreneur'")
        return
    
    post_content = sys.argv[1]
    subreddit = sys.argv[2] if len(sys.argv) > 2 else "general"
    
    indexer = MemoryIndexer('sqlite:///./reddit_os.db')
    
    result = await indexer.generate_response_suggestion(post_content, subreddit)
    
    print(f"\n🔍 Similar responses in your database: {len(result.get('similar_context', []))}")
    print("\n💡 Response Suggestions:\n")
    
    for i, s in enumerate(result.get('suggestions', [])):
        print(f"--- Option #{i+1}: {s.get('tone', 'N/A')} ---")
        print(s.get('content', 'No content'))
        print(f"\nExpected karma: {s.get('expected_karma', 'N/A')}")
        print(f"Why it works: {s.get('reason', 'N/A')}")
        print()

if __name__ == "__main__":
    asyncio.run(main())
