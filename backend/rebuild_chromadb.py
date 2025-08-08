#!/usr/bin/env python3
"""
Rebuild ChromaDB from content_chunks.json
Run this script to initialize/reset your database with the correct schema
"""

import json
import chromadb
from chromadb.config import Settings
import os
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

def rebuild_database():
    """Rebuild ChromaDB from content_chunks.json"""
    
    print("🚀 Starting ChromaDB rebuild...")
    
    # Load content chunks
    print("📚 Loading content chunks...")
    try:
        with open('content_chunks.json', 'r') as f:
            chunks = json.load(f)
        print(f"✅ Loaded {len(chunks)} chunks")
    except FileNotFoundError:
        print("❌ content_chunks.json not found! Make sure it's in the current directory.")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
        return False
    
    # Initialize ChromaDB (this will create a new database or clear existing)
    print("🔄 Initializing ChromaDB...")
    try:
        # Remove existing database if it exists
        import shutil
        if os.path.exists("./chroma_db_free"):
            shutil.rmtree("./chroma_db_free")
            print("🗑️  Removed old database")
        
        client = chromadb.PersistentClient(path="./chroma_db_free")
        print(f"📁 ChromaDB client created, path: ./chroma_db_free")
        
        # List existing collections
        existing_collections = client.list_collections()
        print(f"📋 Existing collections: {[c.name for c in existing_collections]}")
        
        # Create collection with updated schema
        collection = client.create_collection(
            name="crossmint_docs",
            metadata={"description": "Crossmint support documentation"}
        )
        print("✅ Created new collection: crossmint_docs")
        
        # Verify collection was created
        all_collections = client.list_collections()
        print(f"📋 All collections after creation: {[c.name for c in all_collections]}")
        
    except Exception as e:
        print(f"❌ ChromaDB initialization error: {e}")
        return False
    
    # Load embedding model
    print("🤖 Loading embedding model...")
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Embedding model loaded")
    except Exception as e:
        print(f"❌ Error loading embedding model: {e}")
        return False
    
    # Process and add chunks
    print("📝 Processing and adding chunks to database...")
    batch_size = 50
    
    try:
        for i in tqdm(range(0, len(chunks), batch_size), desc="Adding chunks"):
            batch = chunks[i:i + batch_size]
            
            # Prepare batch data
            documents = []
            metadatas = []
            ids = []
            
            for j, chunk in enumerate(batch):
                chunk_id = f"chunk_{i + j}"
                
                # Extract content and metadata
                content = chunk.get('content', chunk.get('text', ''))
                if not content:
                    print(f"⚠️  Skipping empty chunk {chunk_id}")
                    continue
                
                # Build metadata
                metadata = {
                    'source': chunk.get('source', 'unknown'),
                    'topic': chunk.get('topic', chunk.get('category', 'general')),
                    'chunk_index': chunk.get('chunk_index', i + j),
                }
                
                # Add any additional metadata fields
                for key in ['title', 'url', 'section', 'category']:
                    if key in chunk and chunk[key]:
                        metadata[key] = str(chunk[key])
                
                documents.append(content)
                metadatas.append(metadata)
                ids.append(chunk_id)
            
            if documents:  # Only add if we have valid documents
                # Generate embeddings
                embeddings = model.encode(documents).tolist()
                
                # Add to collection
                collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids,
                    embeddings=embeddings
                )
    
    except Exception as e:
        print(f"❌ Error processing chunks: {e}")
        return False
    
    # Verify the database
    print("🔍 Verifying database...")
    try:
        count = collection.count()
        print(f"✅ Database rebuilt successfully!")
        print(f"📊 Total documents: {count}")
        
        # Test a sample query
        if count > 0:
            results = collection.query(
                query_texts=["How do I create an NFT?"],
                n_results=1
            )
            if results['documents']:
                print("✅ Sample query successful")
                print(f"📄 Sample result: {results['documents'][0][0][:100]}...")
            
    except Exception as e:
        print(f"❌ Error verifying database: {e}")
        return False
    
    print("🎉 ChromaDB rebuild complete!")
    print("💡 You can now restart your FastAPI server")
    return True

if __name__ == "__main__":
    success = rebuild_database()
    if not success:
        exit(1)