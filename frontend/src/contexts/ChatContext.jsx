import React, { createContext, useContext, useReducer, useEffect, useRef } from 'react';
import ApiService from '../services/api';

const ChatContext = createContext();

// Chat state management
const initialState = {
  isOpen: false,
  isMinimized: false,
  messages: [],
  sessionId: null,
  isLoading: false,
  error: null
};

function chatReducer(state, action) {
  switch (action.type) {
    case 'SET_OPEN':
      return { ...state, isOpen: action.payload };
    case 'SET_MINIMIZED':
      return { ...state, isMinimized: action.payload };
    case 'SET_SESSION_ID':
      return { ...state, sessionId: action.payload };
    case 'ADD_MESSAGE':
      return { ...state, messages: [...state.messages, action.payload] };
    case 'SET_MESSAGES':
      return { ...state, messages: action.payload };
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'RESET_CHAT':
      return { ...initialState };
    default:
      return state;
  }
}

export const ChatProvider = ({ children }) => {
  const [state, dispatch] = useReducer(chatReducer, initialState);
  const isInitialMount = useRef(true);

  // Clear chat state on page refresh to start fresh session
  useEffect(() => {
    // Clear any existing chat session to force new session on page load
    localStorage.removeItem('chatState');
    console.log('Chat session cleared - will create new session on first message');
  }, []);

  // Validate if session still exists on the server
  const validateSession = async (sessionId) => {
    try {
      await ApiService.getChatHistory(sessionId);
    } catch (error) {
      if (error.message && error.message.includes('Chat session not found')) {
        console.log('Saved session is invalid, will create new one when needed');
        // Don't clear the session immediately, let it be handled when user tries to send a message
      }
    }
  };

  // Save chat state to localStorage whenever it changes (but skip initial mount)
  useEffect(() => {
    // Skip saving on initial mount since we just cleared it
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }
    
    const stateToSave = {
      sessionId: state.sessionId,
      messages: state.messages,
      isOpen: state.isOpen,
      isMinimized: state.isMinimized
    };
    localStorage.setItem('chatState', JSON.stringify(stateToSave));
  }, [state.sessionId, state.messages, state.isOpen, state.isMinimized]);

  const createChatSession = async () => {
    try {
      const response = await ApiService.createChatSession();
      dispatch({ type: 'SET_SESSION_ID', payload: response.session_id });
      
      // Add welcome message
      const welcomeMessage = {
        type: 'agent',
        content: 'Hello! I\'m your AI investment advisor. I can help you with investment advice, market analysis, stock comparisons, and portfolio recommendations. What would you like to discuss?',
        timestamp: new Date().toISOString()
      };
      
      // If this is a session recovery (messages exist), add a session reset message
      if (state.messages.length > 0) {
        const resetMessage = {
          type: 'system',
          content: 'New chat session created. Previous context may be lost.',
          timestamp: new Date().toISOString()
        };
        dispatch({ type: 'SET_MESSAGES', payload: [resetMessage, welcomeMessage] });
      } else {
        dispatch({ type: 'SET_MESSAGES', payload: [welcomeMessage] });
      }
      
      return response.session_id;
    } catch (error) {
      console.error('Failed to create chat session:', error);
      dispatch({ type: 'SET_ERROR', payload: 'Failed to start chat session' });
      throw error;
    }
  };

  const sendMessage = async (message) => {
    if (!message.trim() || state.isLoading) return;

    // If no session exists, create one first
    let currentSessionId = state.sessionId;
    if (!currentSessionId) {
      try {
        currentSessionId = await createChatSession();
      } catch (error) {
        dispatch({ type: 'SET_ERROR', payload: 'Failed to start chat session' });
        return;
      }
    }

    const userMessage = {
      type: 'user',
      content: message.trim(),
      timestamp: new Date().toISOString()
    };

    dispatch({ type: 'ADD_MESSAGE', payload: userMessage });
    dispatch({ type: 'SET_LOADING', payload: true });
    dispatch({ type: 'SET_ERROR', payload: null });

    try {
      const response = await ApiService.sendChatMessage(currentSessionId, message.trim());
      
      const agentMessage = {
        type: 'agent',
        content: response.content,
        rationale: response.rationale,
        comparison: response.comparison,
        timestamp: response.timestamp
      };

      dispatch({ type: 'ADD_MESSAGE', payload: agentMessage });
    } catch (error) {
      console.error('Failed to send message:', error);
      
      // If session not found, try creating a new session and retry once
      if (error.message && error.message.includes('Chat session not found')) {
        console.log('Session not found, creating new session and retrying...');
        try {
          const newSessionId = await createChatSession();
          const response = await ApiService.sendChatMessage(newSessionId, message.trim());
          
          const agentMessage = {
            type: 'agent',
            content: response.content,
            rationale: response.rationale,
            comparison: response.comparison,
            timestamp: response.timestamp
          };

          dispatch({ type: 'ADD_MESSAGE', payload: agentMessage });
        } catch (retryError) {
          console.error('Failed to send message after retry:', retryError);
          dispatch({ type: 'SET_ERROR', payload: 'Failed to send message. Please try again.' });
          
          // Add error message
          const errorMessage = {
            type: 'agent',
            content: 'Sorry, I encountered an error. Please try again.',
            timestamp: new Date().toISOString()
          };
          dispatch({ type: 'ADD_MESSAGE', payload: errorMessage });
        }
      } else {
        dispatch({ type: 'SET_ERROR', payload: 'Failed to send message. Please try again.' });
        
        // Add error message
        const errorMessage = {
          type: 'agent',
          content: 'Sorry, I encountered an error. Please try again.',
          timestamp: new Date().toISOString()
        };
        dispatch({ type: 'ADD_MESSAGE', payload: errorMessage });
      }
      
      // Add error message
      const errorMessage = {
        type: 'agent',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString()
      };
      dispatch({ type: 'ADD_MESSAGE', payload: errorMessage });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const loadChatHistory = async (sessionId) => {
    try {
      const response = await ApiService.getChatHistory(sessionId);
      dispatch({ type: 'SET_MESSAGES', payload: response.messages });
    } catch (error) {
      console.error('Failed to load chat history:', error);
      dispatch({ type: 'SET_ERROR', payload: 'Failed to load chat history' });
    }
  };

  const toggleChat = () => {
    dispatch({ type: 'SET_OPEN', payload: !state.isOpen });
  };

  const minimizeChat = () => {
    dispatch({ type: 'SET_MINIMIZED', payload: !state.isMinimized });
  };

  const closeChat = () => {
    dispatch({ type: 'SET_OPEN', payload: false });
  };

  const resetChat = () => {
    dispatch({ type: 'RESET_CHAT' });
    localStorage.removeItem('chatState');
  };

  const value = {
    ...state,
    createChatSession,
    sendMessage,
    loadChatHistory,
    toggleChat,
    minimizeChat,
    closeChat,
    resetChat
  };

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};