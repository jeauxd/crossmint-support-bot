#!/usr/bin/env python3
"""
Upload documents from content_chunks.json to Pinecone using OpenAI embeddings
Run this script from your backend directory where content_chunks.json is located
"""

import json
import os
from openai import OpenAI
from pinecone import Pinecone
from tqdm import tqdm
import time

def upload_to_pinecone():
    """Upload all documents to Pinecone using OpenAI embeddings"""
    
    # Get API keys
    pinecone_api_key = input("Enter your Pinecone API key: ")
    openai_api_key = input("Enter your OpenAI API key: ")
    
    # Initialize clients
    pc = Pinecone(api_key=pinecone_api_key)
    openai_client = OpenAI(api_key=openai_api_key)
    
    # Connect to index
    index_name = "crossmint-docs"
    index = pc.Index(index_name)
    
    print(f"✅ Connected to Pinecone index: {index_name}")
    
    # Load documents
    print("📚 Loading content chunks...")
    with open('content_chunks.json', 'r') as f:
        chunks = json.load(f)
    print(f"✅ Loaded {len(chunks)} chunks")
    
    print("🤖 Using OpenAI embeddings...")
    
    # Process in batches
    batch_size = 20  # Smaller batches for API rate limits
    total_uploaded = 0
    
    print("📤 Uploading to Pinecone with OpenAI embeddings...")
    
    for i in tqdm(range(0, len(chunks), batch_size), desc="Uploading batches"):
        batch = chunks[i:i + batch_size]
        
        # Prepare batch data
        vectors = []
        texts_to_embed = []
        batch_metadata = []
        
        for j, chunk in enumerate(batch):
            chunk_id = f"chunk_{i + j}"
            
            # Get content
            content = chunk.get('content', chunk.get('text', ''))
            if not content:
                continue
            
            texts_to_embed.append(content)
            
            # Prepare metadata
            metadata = {
                'content': content,
                'source': chunk.get('source', 'unknown'),
                'title': chunk.get('title', 'Crossmint Documentation'),
                'url': chunk.get('url', 'https://docs.crossmint.com'),
                'topic': chunk.get('topic', chunk.get('category', 'general')),
                'chunk_index': chunk.get('chunk_index', i + j)
            }
            
            batch_metadata.append((chunk_id, metadata))
        
        if not texts_to_embed:
            continue
        
        # Generate embeddings with OpenAI
        try:
            response = openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=texts_to_embed
            )
            
            # Prepare vectors for Pinecone
            for idx, embedding_data in enumerate(response.data):
                chunk_id, metadata = batch_metadata[idx]
                vectors.append({
                    'id': chunk_id,
                    'values': embedding_data.embedding,
                    'metadata': metadata
                })
            
            # Upload batch to Pinecone
            if vectors:
                index.upsert(vectors=vectors)
                total_uploaded += len(vectors)
                
            # Rate limiting - be nice to OpenAI API
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Error processing batch {i}: {e}")
            continue
    
    print(f"🎉 Upload complete! {total_uploaded} documents uploaded to Pinecone")
    
    # Test query
    print("🔍 Testing with sample query...")
    try:
        query_response = openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=["How do I create an NFT?"]
        )
        query_embedding = query_response.data[0].embedding
        
        results = index.query(vector=query_embedding, top_k=3, include_metadata=True)
        
        print("✅ Sample query results:")
        for match in results['matches']:
            print(f"  - {match['metadata']['title']} (score: {match['score']:.3f})")
            
    except Exception as e:
        print(f"❌ Error testing query: {e}")
    
    print(f"💡 Your Pinecone API key: {pinecone_api_key}")
    print(f"💡 Your OpenAI API key: {openai_api_key}")
    print("💡 Save these API keys - you'll need them for your Vercel app!")

if __name__ == "__main__":
    upload_to_pinecone()