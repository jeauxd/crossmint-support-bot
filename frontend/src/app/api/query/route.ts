import { NextRequest, NextResponse } from 'next/server';
import OpenAI from 'openai';

export async function POST(request: NextRequest) {
  try {
    const { query } = await request.json();
    
    if (!query) {
      return NextResponse.json(
        { error: "Query is required" },
        { status: 400 }
      );
    }

    // Initialize OpenAI
    const openai = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY,
    });

    // Search Pinecone for relevant documents
    const pineconeResponse = await fetch('https://crossmint-docs-sy801vw.svc.aped-4627-b74a.pinecone.io/query', {
      method: 'POST',
      headers: {
        'Api-Key': process.env.PINECONE_API_KEY || '',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        vector: await getQueryEmbedding(query),
        topK: 5,
        includeMetadata: true,
      }),
    });

    const pineconeData = await pineconeResponse.json();
    const matches = pineconeData.matches || [];

    // Extract context and sources from Pinecone results
    const context = matches.map((match: { metadata: { content: string } }) => match.metadata.content).join('\n\n');
    const sources = matches.map((match: { metadata: { title: string, url: string }, score: number }) => ({
      title: match.metadata.title,
      url: match.metadata.url,
      relevance_score: match.score,
    }));

    // Generate response with OpenAI
    const completion = await openai.chat.completions.create({
      model: "gpt-3.5-turbo",
      messages: [
        {
          role: "system",
          content: "You are a helpful customer support assistant for Crossmint. Use the provided documentation to answer questions about Crossmint's APIs and services. Be specific and helpful."
        },
        {
          role: "user",
          content: `Context from Crossmint documentation:\n${context}\n\nQuestion: ${query}\n\nPlease provide a helpful answer based on the documentation context.`
        }
      ],
      temperature: 0.1,
      max_tokens: 800
    });

    // Format response
    const result = {
      query,
      response: completion.choices[0].message.content,
      sources,
      timestamp: new Date().toISOString(),
      method: "RAG with Pinecone + OpenAI"
    };

    return NextResponse.json(result);

  } catch (error) {
    console.error('Error:', error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

// Helper function to get embeddings (using OpenAI's embedding API)
async function getQueryEmbedding(text: string): Promise<number[]> {
  const openai = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY,
  });

  const response = await openai.embeddings.create({
    model: "text-embedding-ada-002",
    input: text,
  });

  return response.data[0].embedding;
}

export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}