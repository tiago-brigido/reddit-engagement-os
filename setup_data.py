#!/usr/bin/env python3
"""Setup script to populate database with your Reddit content"""
import asyncio
import os
import sys
sys.path.insert(0, '/Users/tiago/reddit-engagement-os')
os.environ['DATABASE_URL'] = 'sqlite:///./reddit_os.db'

from lib.indexer import MemoryIndexer

async def main():
    indexer = MemoryIndexer('sqlite:///./reddit_os.db')
    
    # Index the main post
    post_id = await indexer.index_conversation({
        'reddit_id': 't3_xsk20b',
        'subreddit': 'sales',
        'title': "25, 2.5 years into payroll sales - what now?",
        'post_url': 'https://reddit.com/r/sales/comments/xsk20b',
        'content': """
        25M, 2.5 years selling payroll/HCM to small businesses (top performer, multiple President's Club wins). 
        Need to hit 3 years for my 401k match to vest, so I've got a runway to figure out my next move.
        
        Three paths:
        1. Move into PEO sales
        2. Switch industries entirely
        3. Go all-in on entrepreneurship
        """,
        'author': 'Gr8ful007',
        'score': 25,
        'num_comments': 12,
        'created_utc': '',
        'permalink': '/r/sales/comments/xsk20b/'
    })
    print(f"✅ Indexed post: {post_id}")
    
    # Index your comment
    resp_id = await indexer.index_response({
        'content': "Based on what we know. #1, because you already have a deep knowledge of the market, it's actually a hot b2b market (solves your point 2) with public companies (Workday, ADP), huge startups (Deel and Rippling) and new players coming out like warp. I believe there is more value in just doubling down into what you are already doing. The company you pick depends on what you wanna trade off (time vs money).",
        'score': 15,
        'author': 'tmcbrigido',
        'ai_generated': False,
        'model_used': 'user-provided'
    })
    print(f"✅ Indexed your comment: {resp_id}")

asyncio.run(main())
