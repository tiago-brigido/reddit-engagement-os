#!/usr/bin/env python3
"""
Quick script to find your Reddit comments by nickname/author
Usage: python3 find_my_comments.py "tmcbrigido"
"""

import sys
import os
sys.path.insert(0, '/Users/tiago/reddit-engagement-os')
os.environ['DATABASE_URL'] = 'sqlite:///./reddit_os.db'

from lib.indexer import MemoryIndexer

def main():
    nickname = sys.argv[1] if len(sys.argv) > 1 else "tmcbrigido"
    
    indexer = MemoryIndexer('sqlite:///./reddit_os.db')
    
    print(f"Searching for responses by '{nickname}'...\n")
    
    # Find all responses by this author
    results = indexer.find_responses_by_author(nickname)
    
    if not results:
        print("No responses found for this author.")
        return
    
    print(f"Found {len(results)} responses:\n")
    for r in results:
        print(f"ID: {r['id']}")
        print(f"Score/Karma: {r['score']}")
        print(f"AI Generated: {r['ai_generated']}")
        print(f"Content: {r['content'][:200]}...")
        print("---\n")
    
    # Also search by content similarity
    print(f"\nSearching for responses similar to '{nickname}'...\n")
    similar = indexer.search_responses_by_content(nickname)
    
    for r in similar:
        print(f"ID: {r['id']}, Author: {r['author']}, Score: {r['score']}, Similarity: {r['similarity']:.3f}")
        print(f"  {r['content'][:100]}...")
        print()

if __name__ == "__main__":
    main()
