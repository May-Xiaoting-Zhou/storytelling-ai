// API configuration for storytelling-ai

const isDevelopment = import.meta.env.MODE === 'development';

export const API_URL = isDevelopment ? '' : process.env.REACT_APP_API_URL;

export const API_ENDPOINTS = {
  STORY: '/api/story',
  // Add more endpoints as needed
};

export const DEBUG = {
  ENABLE_LOGS: isDevelopment,
  LOG_API_CALLS: isDevelopment,
  MOCK_RESPONSES: false,
};

export const API_TIMEOUT = 30000; // 30 seconds