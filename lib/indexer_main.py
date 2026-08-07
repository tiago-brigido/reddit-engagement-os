from lib.indexer import MemoryIndexer
from api.main import engine
import asyncio
from db.schema import Conversation, Response

def run_indexer():
    indexer = MemoryIndexer(engine)
    return indexer

if __name__ == "__main__":
    indexer = run_indexer()
    print("Reddit Engagement OS Indexer Ready")
