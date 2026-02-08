import React, { useState, useEffect, useRef } from 'react';
import { 
  MessageCircle, X, Send, Bot, User, Minimize2, Maximize2, 
  AlertCircle, Loader 
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { useChat } from '../contexts/ChatContext';
import { useAuth } from '../contexts/AuthContext';

const ChatBot = () => {
  const { user } = useAuth();
  const {
    isOpen,
    isMinimized,
    messages,
    sessionId,
    isLoading,
    error,
    createChatSession,
    sendMessage,
    toggleChat,
    minimizeChat,
    closeChat
  } = useChat();

  const [inputMessage, setInputMessage] = useState('');
  const messagesEndRef = useRef(null);

  // Scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize chat session when component mounts
  useEffect(() => {
    if (user && !sessionId) {
      createChatSession();
    }
  }, [user, sessionId, createChatSession]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;
    
    await sendMessage(inputMessage.trim());
    setInputMessage('');
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatMessage = (message) => {
    let content = message.content;
    
    // Add rationale if available
    if (message.rationale && message.rationale.trim()) {
      content += `\n\n**Rationale:** ${message.rationale}`;
    }
    
    // Add comparison if available
    if (message.comparison && message.comparison.trim()) {
      content += `\n\n**Comparison:** ${message.comparison}`;
    }
    
    return content;
  };

  const MessageContent = ({ content, isAI }) => {
    if (isAI) {
      return (
        <div className="markdown-content">
          <ReactMarkdown
            components={{
              // Customize heading styles
              h1: ({children}) => <h1 className="text-lg font-semibold mb-2 text-slate-100">{children}</h1>,
              h2: ({children}) => <h2 className="text-base font-semibold mb-2 text-slate-100">{children}</h2>,
              h3: ({children}) => <h3 className="text-sm font-semibold mb-1 text-slate-300">{children}</h3>,
              // Customize bold text
              strong: ({children}) => <strong className="font-semibold text-cyan-200">{children}</strong>,
              // Customize paragraphs
              p: ({children}) => <p className="mb-2 last:mb-0 leading-relaxed text-sm">{children}</p>,
              // Customize lists
              ul: ({children}) => <ul className="list-disc list-inside mb-2 space-y-1 ml-2">{children}</ul>,
              ol: ({children}) => <ol className="list-decimal list-inside mb-2 space-y-1 ml-2">{children}</ol>,
              li: ({children}) => <li className="text-sm leading-relaxed">{children}</li>,
              // Customize code
              code: ({children}) => <code className="bg-slate-800/80 px-1 py-0.5 rounded text-xs font-mono text-cyan-200">{children}</code>,
              // Customize blockquotes
              blockquote: ({children}) => <blockquote className="border-l-4 border-cyan-400/40 pl-3 italic text-slate-300 my-2">{children}</blockquote>
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
      );
    } else {
      // For user messages, keep simple text formatting
      const lines = content.split('\n');
      return (
        <div>
          {lines.map((line, index) => {
            if (line.trim() === '') {
              return <div key={index} className="h-2" />;
            } else {
              return (
                <div key={index} className="leading-relaxed">
                  {line}
                </div>
              );
            }
          })}
        </div>
      );
    }
  };

  if (!user) {
    return null;
  }

  return (
    <>
      {/* Chat Button */}
      {!isOpen && (
        <button
          onClick={toggleChat}
          className="fixed bottom-6 right-6 bg-cyan-400 hover:bg-cyan-300 text-slate-900 rounded-full p-4 shadow-[0_18px_40px_rgba(34,211,238,0.4)] transition-all duration-200 hover:scale-110 z-50"
        >
          <MessageCircle className="h-6 w-6" />
          <span className="absolute -top-1 -right-1 bg-emerald-300 text-slate-900 text-xs rounded-full h-5 w-5 flex items-center justify-center">
            AI
          </span>
        </button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div className={`fixed bottom-6 right-6 bg-slate-950/90 backdrop-blur-xl border border-slate-800/70 rounded-2xl shadow-[0_25px_60px_rgba(2,6,23,0.6)] z-50 transition-all duration-300 ${
          isMinimized ? 'w-80 h-16' : 'w-[500px] h-[700px]'
        }`}>
          {/* Chat Header */}
          <div className="bg-slate-900/80 text-slate-100 p-4 rounded-t-2xl border-b border-slate-800/70 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <img src="/icons/iconpng.png" alt="TuniTrAide" className="h-6 w-6" />
              <span className="font-medium">TuniTr<span className="text-cyan-400">AI</span>de Advisor</span>
              <span className="text-xs bg-emerald-500/15 text-emerald-200 px-2 py-1 rounded-full border border-emerald-400/30">Online</span>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={minimizeChat}
                className="hover:bg-slate-800/80 p-1 rounded"
              >
                {isMinimized ? <Maximize2 className="h-4 w-4" /> : <Minimize2 className="h-4 w-4" />}
              </button>
              <button
                onClick={closeChat}
                className="hover:bg-slate-800/80 p-1 rounded"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {!isMinimized && (
            <>
              {/* Chat Messages */}
              <div className="h-[580px] overflow-y-auto p-4 space-y-4">
                {error && (
                  <div className="flex items-center space-x-2 text-rose-200 bg-rose-500/10 border border-rose-400/30 p-2 rounded-lg">
                    <AlertCircle className="h-4 w-4" />
                    <span className="text-sm">{error}</span>
                  </div>
                )}

                {messages.map((message, index) => {
                  // Handle system messages differently
                  if (message.type === 'system') {
                    return (
                      <div key={index} className="flex justify-center">
                        <div className="bg-amber-500/10 text-amber-200 text-sm px-3 py-2 rounded-lg border border-amber-400/30">
                          {message.content}
                        </div>
                      </div>
                    );
                  }

                  return (
                    <div
                      key={index}
                      className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div className={`flex items-start space-x-2 max-w-[85%] ${
                        message.type === 'user' ? 'flex-row-reverse space-x-reverse' : ''
                      }`}>
                        <div className={`rounded-full p-2 ${
                          message.type === 'user' 
                            ? 'bg-cyan-400 text-slate-900' 
                            : 'bg-slate-800 text-slate-200'
                        }`}>
                          {message.type === 'user' ? (
                            <User className="h-3 w-3" />
                          ) : (
                            <Bot className="h-3 w-3" />
                          )}
                        </div>
                        <div className={`rounded-lg p-3 ${
                          message.type === 'user'
                            ? 'bg-cyan-400 text-slate-900'
                            : 'bg-slate-900/70 text-slate-100 border border-slate-800/70'
                        }`}>
                          <MessageContent 
                            content={formatMessage(message)} 
                            isAI={message.type === 'agent'} 
                          />
                          <div className={`text-xs mt-2 opacity-70`}>
                            {new Date(message.timestamp).toLocaleTimeString()}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}

                {isLoading && (
                  <div className="flex justify-start">
                    <div className="flex items-start space-x-2">
                      <div className="bg-slate-800 text-slate-200 rounded-full p-2">
                        <Bot className="h-3 w-3" />
                      </div>
                      <div className="bg-slate-900/70 text-slate-100 rounded-lg p-3 border border-slate-800/70">
                        <div className="flex items-center space-x-2">
                          <Loader className="h-4 w-4 animate-spin" />
                          <span>Analyzing your request...</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Chat Input */}
              <div className="border-t border-slate-800/70 p-4">
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Ask about investments, stocks, or market analysis..."
                    className="input-field text-sm"
                    disabled={isLoading || !sessionId}
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={!inputMessage.trim() || isLoading || !sessionId}
                    className="btn-primary px-3 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Send className="h-4 w-4" />
                  </button>
                </div>
                <div className="text-xs text-slate-500 mt-2">
                  Try: "Should I buy Apple stock?" or "Compare AAPL vs MSFT"
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </>
  );
};

export default ChatBot;