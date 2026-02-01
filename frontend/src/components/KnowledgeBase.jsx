import React, { useState, useRef, useEffect } from 'react';
import api from '../services/api';

export default function KnowledgeBase() {
  const [activeAgent, setActiveAgent] = useState('customer'); // 'customer' or 'ops'
  const [conversations, setConversations] = useState({
    customer: { messages: [], sessionId: null },
    ops: { messages: [], sessionId: null }
  });
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversations]);

  const currentConversation = conversations[activeAgent];

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = { role: 'user', content: input.trim(), timestamp: new Date() };
    
    // Add user message to conversation
    setConversations(prev => ({
      ...prev,
      [activeAgent]: {
        ...prev[activeAgent],
        messages: [...prev[activeAgent].messages, userMessage]
      }
    }));
    
    const questionText = input.trim();
    setInput('');
    setLoading(true);

    try {
      const endpoint = activeAgent === 'customer' ? '/api/customer/ask' : '/api/ops/ask';
      const response = await api.post(
        endpoint,
        {
          question: questionText,
          session_id: currentConversation.sessionId // Continue conversation
        },
        // Bedrock agent calls can easily take >10s.
        { timeout: 180000 }
      );

      const assistantMessage = {
        role: 'assistant',
        content: response.data.answer,
        timestamp: new Date(),
        agentId: response.data.agent_id,
        sessionId: response.data.session_id
      };

      // Add assistant response to conversation
      setConversations(prev => ({
        ...prev,
        [activeAgent]: {
          messages: [...prev[activeAgent].messages, assistantMessage],
          sessionId: response.data.session_id // Update session ID
        }
      }));

    } catch (err) {
      const errorMessage = {
        role: 'error',
        content: err.response?.data?.detail || err.message,
        timestamp: new Date()
      };
      
      setConversations(prev => ({
        ...prev,
        [activeAgent]: {
          ...prev[activeAgent],
          messages: [...prev[activeAgent].messages, errorMessage]
        }
      }));
    } finally {
      setLoading(false);
    }
  };

  const handleClearChat = () => {
    if (confirm(`Clear ${activeAgent} chat history?`)) {
      setConversations(prev => ({
        ...prev,
        [activeAgent]: { messages: [], sessionId: null }
      }));
    }
  };

  const handleSwitchAgent = (agent) => {
    setActiveAgent(agent);
    setInput('');
  };

  const agentConfig = {
    customer: {
      name: 'Customer Support',
      icon: '🎓',
      description: 'HUTECH programs, courses, enrollment, billing',
      color: 'blue',
      examples: [
        'What programs does HUTECH offer?',
        'How do I enroll in a course?',
        'Tell me about admission requirements'
      ]
    },
    ops: {
      name: 'DevOps Assistant',
      icon: '⚙️',
      description: 'ALB, ASG, deployments, infrastructure',
      color: 'green',
      examples: [
        'How to scale the ASG?',
        'Explain instance refresh process',
        'What are ALB health check best practices?'
      ]
    }
  };

  const config = agentConfig[activeAgent];

  return (
    <div className="h-[calc(100vh-12rem)]">
      {/* Header with Agent Tabs */}
      <div className="mb-4">
        <h2 className="text-2xl font-bold text-gray-800 mb-2">AI Assistant</h2>
        <div className="flex gap-3 mb-3">
          {Object.entries(agentConfig).map(([key, cfg]) => (
            <button
              key={key}
              onClick={() => handleSwitchAgent(key)}
              className={`flex-1 px-4 py-3 rounded-lg transition shadow-sm ${
                activeAgent === key
                  ? `bg-${cfg.color}-500 text-white shadow-md`
                  : 'bg-white text-gray-700 hover:bg-gray-50 border'
              }`}
            >
              <div className="flex items-center justify-center gap-2">
                <span className="text-2xl">{cfg.icon}</span>
                <div className="text-left">
                  <div className="font-semibold">{cfg.name}</div>
                  <div className={`text-xs ${activeAgent === key ? 'text-white/80' : 'text-gray-500'}`}>
                    {cfg.description}
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Chat Container */}
      <div className="bg-white rounded-lg shadow-lg flex flex-col h-full">
        
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {currentConversation.messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-gray-500">
              <span className="text-6xl mb-4">{config.icon}</span>
              <h3 className="text-xl font-semibold mb-2">{config.name}</h3>
              <p className="text-sm mb-4 text-center max-w-md">{config.description}</p>
              <div className="text-sm text-left">
                <p className="font-medium mb-2">Try asking:</p>
                <ul className="space-y-1 text-gray-600">
                  {config.examples.map((ex, i) => (
                    <li key={i} className="flex items-start">
                      <span className="mr-2">•</span>
                      <button
                        onClick={() => setInput(ex)}
                        className="text-left hover:text-blue-600 transition"
                      >
                        {ex}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            currentConversation.messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg px-4 py-3 ${
                    msg.role === 'user'
                      ? 'bg-blue-500 text-white'
                      : msg.role === 'error'
                      ? 'bg-red-100 text-red-800 border border-red-300'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {msg.role === 'assistant' && (
                    <div className="flex items-center gap-2 mb-2 text-sm opacity-70">
                      <span>{config.icon}</span>
                      <span>{config.name}</span>
                    </div>
                  )}
                  <div className="whitespace-pre-wrap break-words">{msg.content}</div>
                  <div
                    className={`text-xs mt-2 ${
                      msg.role === 'user' ? 'text-white/70' : 'text-gray-500'
                    }`}
                  >
                    {msg.timestamp.toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))
          )}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-lg px-4 py-3">
                <div className="flex items-center gap-2">
                  <div className="animate-bounce">●</div>
                  <div className="animate-bounce delay-100">●</div>
                  <div className="animate-bounce delay-200">●</div>
                  <span className="ml-2 text-gray-500">Thinking...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t p-4">
          <form onSubmit={handleSend} className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={`Ask ${config.name}...`}
              className="flex-1 border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Send
            </button>
            {currentConversation.messages.length > 0 && (
              <button
                type="button"
                onClick={handleClearChat}
                className="bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300 transition"
              >
                Clear
              </button>
            )}
          </form>
          {currentConversation.sessionId && (
            <div className="text-xs text-gray-500 mt-2">
              Session: {currentConversation.sessionId.substring(0, 8)}...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

