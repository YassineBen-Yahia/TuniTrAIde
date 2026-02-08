import React, { createContext, useContext, useReducer, useEffect } from 'react';
import ApiService from '../services/api';

// Auth Context
const AuthContext = createContext();

// Auth Actions
const authActions = {
  LOGIN_START: 'LOGIN_START',
  LOGIN_SUCCESS: 'LOGIN_SUCCESS',
  LOGIN_FAILURE: 'LOGIN_FAILURE',
  LOGOUT: 'LOGOUT',
  SET_USER: 'SET_USER',
  CLEAR_ERROR: 'CLEAR_ERROR',
};

// Initial State
const initialState = {
  user: null,
  token: localStorage.getItem('token'),
  isAuthenticated: !!localStorage.getItem('token'),
  isLoading: false,
  error: null,
};

// Auth Reducer
function authReducer(state, action) {
  switch (action.type) {
    case authActions.LOGIN_START:
      return {
        ...state,
        isLoading: true,
        error: null,
      };
    case authActions.LOGIN_SUCCESS:
      return {
        ...state,
        user: action.payload.user,
        token: action.payload.token,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      };
    case authActions.LOGIN_FAILURE:
      return {
        ...state,
        user: null,
        token: null,
        isAuthenticated: false, // change back to false
        isLoading: false,
        error: action.payload,
      };
    case authActions.LOGOUT:
      return {
        ...state,
        user: null,
        token: null,
        isAuthenticated: false, // change back to false 
        isLoading: false,
        error: null,
      };
    case authActions.SET_USER:
      return {
        ...state,
        user: action.payload,
      };
    case authActions.CLEAR_ERROR:
      return {
        ...state,
        error: null,
      };
    default:
      return state;
  }
}

// Auth Provider Component
export function AuthProvider({ children }) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Check if user is authenticated on mount
  useEffect(() => {
    if (state.token) {
      fetchCurrentUser();
    }
  }, []);

  const fetchCurrentUser = async () => {
    try {
      const user = await ApiService.getCurrentUser();
      dispatch({ type: authActions.SET_USER, payload: user });
    } catch (error) {
      console.error('Failed to fetch current user:', error);
      logout();
    }
  };

  const login = async (credentials) => {
    dispatch({ type: authActions.LOGIN_START });
    try {
      const response = await ApiService.login(credentials);
      
      // Set token first
      localStorage.setItem('token', response.access_token);
      ApiService.setToken(response.access_token);
      
      // Then fetch user data
      const user = await ApiService.getCurrentUser();
      
      dispatch({
        type: authActions.LOGIN_SUCCESS,
        payload: {
          user: user,
          token: response.access_token,
        },
      });
      return { success: true, user };
    } catch (error) {
      dispatch({
        type: authActions.LOGIN_FAILURE,
        payload: error.message,
      });
      throw error;
    }
  };

  const register = async (userData) => {
    dispatch({ type: authActions.LOGIN_START });
    try {
      const response = await ApiService.register(userData);
      return response;
    } catch (error) {
      dispatch({
        type: authActions.LOGIN_FAILURE,
        payload: error.message,
      });
      throw error;
    }
  };

  const logout = () => {
    ApiService.logout();
    dispatch({ type: authActions.LOGOUT });
  };

  const clearError = () => {
    dispatch({ type: authActions.CLEAR_ERROR });
  };

  const value = {
    ...state,
    login,
    register,
    logout,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Custom Hook
const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export { useAuth };