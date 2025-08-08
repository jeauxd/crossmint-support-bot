from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import json
from datetime import datetime
from sentence_transformers import SentenceTransformer
import chromadb
from openai import OpenAI
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Global variables to store our models and database
embedding_model = None
chroma_client = None
chroma_collection = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global embedding_model, chroma_client, chroma_collection
    
    print("🚀 Starting up FastAPI server...")
    
    # Initialize sentence transformer for embeddings
    print("📚 Loading embedding model...")
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    
    # Initialize ChromaDB client (NEW FORMAT)
    print("🔍 Connecting to ChromaDB...")
    try:
        chroma_client = chromadb.PersistentClient(path="./chroma_db_free")
        
        # List available collections
        collections = chroma_client.list_collections()
        print(f"Available collections: {[col.name for col in collections]}")
        
        # Try to get the collection
        chroma_collection = chroma_client.get_collection("crossmint_docs")
        doc_count = chroma_collection.count()
        print(f"✅ Loaded ChromaDB collection with {doc_count} documents")
        
    except Exception as e:
        print(f"⚠️ ChromaDB not available: {e}")
        print("🔄 Falling back to general knowledge mode")
        chroma_client = None
        chroma_collection = None
    
    print("🎉 FastAPI server ready!")
    
    yield
    
    # Shutdown
    print("👋 Shutting down FastAPI server...")

app = FastAPI(
    title="Crossmint Support Bot API",
    description="RAG-powered customer support API for Crossmint documentation",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS - Updated for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.vercel.app",
        "https://vercel.app",
        "*"  # For development - remove in production if needed
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class QueryRequest(BaseModel):
    query: str
    max_results: Optional[int] = 5

class Source(BaseModel):
    title: str
    url: str
    relevance_score: float

class QueryResponse(BaseModel):
    query: str
    response: str
    sources: List[Source]
    timestamp: str
    method: str

class HealthResponse(BaseModel):
    status: str
    rag_available: bool
    document_count: Optional[int] = None

def semantic_search(query: str, n_results: int = 5) -> List[Dict[str, Any]]:
    """Search for relevant documents using semantic similarity"""
    if not chroma_collection or not embedding_model:
        return []
    
    try:
        # Generate embedding for the query
        query_embedding = embedding_model.encode([query]).tolist()
        
        # Search in ChromaDB
        results = chroma_collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            include=['documents', 'metadatas', 'distances']
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results['documents'][0])):
            formatted_results.append({
                'content': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'similarity': 1 - results['distances'][0][i],  # Convert distance to similarity
            })
        
        return formatted_results
        
    except Exception as e:
        print(f"Error in semantic search: {e}")
        return []

def generate_response(query: str) -> QueryResponse:
    """Generate response using RAG (Retrieval-Augmented Generation)"""
    
    # Step 1: Retrieve relevant documents
    relevant_docs = semantic_search(query, n_results=5)
    
    if not relevant_docs:
        return fallback_response(query)
    
    # Step 2: Prepare context from retrieved documents
    context_parts = []
    sources = []
    
    for doc in relevant_docs:
        context_parts.append(doc['content'])
        sources.append(Source(
            title=doc['metadata'].get('title', 'Crossmint Documentation'),
            url=doc['metadata'].get('url', 'https://docs.crossmint.com'),
            relevance_score=doc['similarity']
        ))
    
    context = "\n\n".join(context_parts)
    
    # Step 3: Generate response with context
    system_prompt = """You are a helpful customer support assistant for Crossmint, a platform for integrating wallets, stablecoins, and blockchain primitives.

Use the provided documentation context to answer the user's question accurately and helpfully. If the context doesn't contain enough information to fully answer the question, say so and provide what information you can from the context.

Always base your answer primarily on the provided context. Be specific and include relevant details from the documentation."""

    user_prompt = f"""Context from Crossmint documentation:
{context}

Question: {query}

Please provide a helpful answer based on the documentation context above."""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=800
        )
        
        return QueryResponse(
            query=query,
            response=response.choices[0].message.content,
            sources=sources,
            timestamp=datetime.now().isoformat(),
            method='RAG (Full Knowledge Base)'
        )
        
    except Exception as e:
        return QueryResponse(
            query=query,
            response=f"I encountered an error generating a response: {str(e)}. Please try again.",
            sources=sources,
            timestamp=datetime.now().isoformat(),
            method='Error'
        )

def fallback_response(query: str) -> QueryResponse:
    """Fallback to general OpenAI knowledge when RAG is unavailable"""
    system_prompt = """You are a helpful customer support assistant for Crossmint, a platform for integrating wallets, stablecoins, and blockchain primitives.

Provide helpful answers about Crossmint's services based on your general knowledge. Always recommend checking the official Crossmint documentation at docs.crossmint.com for the most up-to-date information."""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.1,
            max_tokens=600
        )
        
        return QueryResponse(
            query=query,
            response=response.choices[0].message.content,
            sources=[Source(title='General Knowledge', url='https://docs.crossmint.com', relevance_score=0.5)],
            timestamp=datetime.now().isoformat(),
            method='Fallback (General Knowledge)'
        )
    except Exception as e:
        return QueryResponse(
            query=query,
            response=f"I'm having trouble generating a response right now. Error: {str(e)}. Please try again or check the Crossmint documentation directly.",
            sources=[],
            timestamp=datetime.now().isoformat(),
            method='Error'
        )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    rag_available = chroma_collection is not None
    doc_count = None
    
    if rag_available:
        try:
            doc_count = chroma_collection.count()
        except:
            pass
    
    return HealthResponse(
        status="healthy",
        rag_available=rag_available,
        document_count=doc_count
    )

@app.post("/query", response_model=QueryResponse)
async def ask_question(request: QueryRequest):
    """Main endpoint for asking questions"""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    if not os.getenv('OPENAI_API_KEY'):
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    try:
        response = generate_response(request.query.strip())
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Crossmint Support Bot API", 
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)