'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, ExternalLink, Loader2 } from 'lucide-react';

interface Source {
  title: string;
  url: string;
  relevance_score: number;
}

interface Message {
  id: string;
  content: string;
  isUser: boolean;
  sources?: Source[];
  timestamp: Date;
}

const EXAMPLE_QUESTIONS = [
  "How do I create an NFT with Crossmint?",
  "What is the Crossmint API?",
  "How do I integrate Crossmint wallets?",
  "What are the pricing options?",
  "How do I deploy an NFT collection?",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (messageText: string = input) => {
    if (!messageText.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: messageText.trim(),
      isUser: true,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: messageText.trim() }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: data.response,
        isUser: false,
        sources: data.sources,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: 'Sorry, I encountered an error. Please make sure the backend server is running on http://localhost:8000 and try again.',
        isUser: false,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage();
  };

  const handleExampleClick = (question: string) => {
    setInput(question);
    sendMessage(question);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-blue-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <div className="flex items-center space-x-3">
            <div className="bg-gradient-to-r from-purple-600 to-blue-600 p-2 rounded-lg">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Crossmint Support Assistant</h1>
              <p className="text-gray-600">Get instant help with Crossmint&apos;s APIs and services</p>
            </div>
          </div>
        </div>
      </div>

      {/* Chat Container */}
      <div className="max-w-4xl mx-auto px-4 py-6 flex flex-col h-[calc(100vh-140px)]">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto space-y-6 mb-6">
          {messages.length === 0 && (
            <div className="text-center py-12">
              <Bot className="w-16 h-16 text-purple-400 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-700 mb-2">
                Welcome to Crossmint Support!
              </h2>
              <p className="text-gray-500 mb-8">
                Ask me anything about Crossmint&apos;s APIs, NFT creation, wallet integration, and more.
              </p>
              
              {/* Example Questions */}
              <div className="max-w-2xl mx-auto">
                <h3 className="text-sm font-medium text-gray-700 mb-4">Try asking:</h3>
                <div className="grid gap-2">
                  {EXAMPLE_QUESTIONS.map((question, index) => (
                    <button
                      key={index}
                      onClick={() => handleExampleClick(question)}
                      className="text-left p-3 bg-white rounded-lg border border-gray-200 hover:border-purple-300 hover:bg-purple-50 transition-colors text-sm text-gray-700"
                    >
                      {question}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.isUser ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-3xl flex ${
                  message.isUser ? 'flex-row-reverse' : 'flex-row'
                } items-start space-x-3 ${message.isUser ? 'space-x-reverse' : ''}`}
              >
                {/* Avatar */}
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    message.isUser
                      ? 'bg-gray-100'
                      : 'bg-gradient-to-r from-purple-600 to-blue-600'
                  }`}
                >
                  {message.isUser ? (
                    <User className="w-4 h-4 text-gray-600" />
                  ) : (
                    <Bot className="w-4 h-4 text-white" />
                  )}
                </div>

                {/* Message Bubble */}
                <div
                  className={`rounded-2xl px-4 py-3 ${
                    message.isUser
                      ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white'
                      : 'bg-white border border-gray-200 text-gray-800'
                  }`}
                >
                  <div className="whitespace-pre-wrap">{message.content}</div>

                  {/* Sources */}
                  {message.sources && message.sources.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-gray-100">
                      <h4 className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">
                        Sources
                      </h4>
                      <div className="space-y-2">
                        {message.sources.map((source, index) => (
                          <a
                            key={index}
                            href={source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center justify-between p-2 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors group"
                          >
                            <div className="flex-1 min-w-0">
                              <div className="text-sm font-medium text-gray-900 truncate">
                                {source.title}
                              </div>
                              <div className="text-xs text-gray-500">
                                Relevance: {(source.relevance_score * 100).toFixed(1)}%
                              </div>
                            </div>
                            <ExternalLink className="w-4 h-4 text-gray-400 group-hover:text-gray-600 ml-2 flex-shrink-0" />
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="max-w-3xl flex flex-row items-start space-x-3">
                <div className="w-8 h-8 rounded-full bg-gradient-to-r from-purple-600 to-blue-600 flex items-center justify-center">
                  <Bot className="w-4 h-4 text-white" />
                </div>
                <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3">
                  <div className="flex items-center space-x-2">
                    <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
                    <span className="text-gray-500 text-sm">Thinking...</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Form */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-lg p-4">
          <form onSubmit={handleSubmit} className="flex space-x-4">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask me anything about Crossmint..."
              className="flex-1 border-0 outline-none text-gray-900 placeholder-gray-500"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="bg-gradient-to-r from-purple-600 to-blue-600 text-white p-2 rounded-lg hover:from-purple-700 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 hover:scale-105"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}