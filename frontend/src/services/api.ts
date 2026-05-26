import axios, { AxiosInstance } from 'axios'
import {
  ChatRequest,
  ChatResponse,
  DocumentUploadResponse,
  DocumentListItem,
  QuizResponse,
  AnalyticsDashboardResponse,
  ConversationSession,
  RecommendationRequest,
  RecommendationResponse,
} from '../types'

const BASE_URL = 'http://localhost:8000/api/v1'

const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
)

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'An error occurred'
    return Promise.reject(new Error(message))
  }
)

export const api = {
  // Chat
  sendChat: async (request: ChatRequest): Promise<ChatResponse> => {
    const response = await apiClient.post<ChatResponse>('/chat', request)
    return response.data
  },

  // Documents
  uploadDocument: async (file: File, collectionName: string = 'default'): Promise<DocumentUploadResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('collection_name', collectionName)
    const response = await apiClient.post<DocumentUploadResponse>('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  listDocuments: async (): Promise<DocumentListItem[]> => {
    const response = await apiClient.get<DocumentListItem[]>('/documents')
    return response.data
  },

  deleteDocument: async (documentId: string): Promise<void> => {
    await apiClient.delete(`/documents/${documentId}`)
  },

  // Quiz
  generateQuiz: async (request: { topic: string; num_questions?: number; difficulty?: string }): Promise<QuizResponse> => {
    const response = await apiClient.post<QuizResponse>('/quiz/generate', request)
    return response.data
  },

  // Analytics
  getAnalytics: async (days: number = 7): Promise<AnalyticsDashboardResponse> => {
    const response = await apiClient.get<AnalyticsDashboardResponse>(`/analytics/dashboard?days=${days}`)
    return response.data
  },

  // History
  getHistory: async (): Promise<ConversationSession[]> => {
    const response = await apiClient.get<ConversationSession[]>('/history/sessions')
    return response.data
  },

  getSessionHistory: async (sessionId: string): Promise<ConversationSession> => {
    const response = await apiClient.get<ConversationSession>(`/history/sessions/${sessionId}`)
    return response.data
  },

  deleteSession: async (sessionId: string): Promise<void> => {
    await apiClient.delete(`/history/sessions/${sessionId}`)
  },

  // Recommendations
  getRecommendations: async (request: RecommendationRequest): Promise<RecommendationResponse> => {
    const response = await apiClient.post<RecommendationResponse>('/recommendations', request)
    return response.data
  },
}

export default api
