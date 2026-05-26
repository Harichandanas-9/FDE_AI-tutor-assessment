// Chat types
export interface SourceReference {
  document_id: string
  document_name: string
  page_number?: number
  chunk_text: string
  relevance_score: number
}

export interface EvaluationMetrics {
  faithfulness: number
  answer_relevance: number
  context_precision: number
  context_recall: number
  overall_score: number
  pass_fail: 'pass' | 'fail'
}

export interface AgentTrace {
  agent_name: string
  action: string
  input?: string
  output?: string
  duration_ms: number
  status: 'success' | 'error' | 'skipped'
}

export interface ChatRequest {
  query: string
  session_id?: string
  mode?: 'chat' | 'explain' | 'summarize' | 'notes'
  collection_name?: string
}

export interface ChatResponse {
  answer: string
  session_id: string
  confidence_score: number
  sources: SourceReference[]
  evaluation_metrics: EvaluationMetrics
  agent_traces: AgentTrace[]
  follow_up_topics: string[]
  processing_time_ms: number
  mode: string
}

// Document types
export interface DocumentUploadResponse {
  document_id: string
  filename: string
  collection_name: string
  chunks_created: number
  status: string
  message: string
}

export interface DocumentListItem {
  document_id: string
  filename: string
  collection_name: string
  upload_date: string
  chunk_count: number
  status: string
}

// Quiz types
export interface QuizQuestion {
  question: string
  options: string[]
  correct_answer: string
  explanation: string
  difficulty: 'easy' | 'medium' | 'hard'
}

export interface QuizResponse {
  topic: string
  questions: QuizQuestion[]
  total_questions: number
  estimated_time_minutes: number
}

// Conversation/History types
export interface ConversationMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  confidence_score?: number
  sources?: SourceReference[]
}

export interface ConversationSession {
  session_id: string
  created_at: string
  last_active: string
  message_count: number
  messages: ConversationMessage[]
  summary?: string
}

// Analytics types
export interface EvaluationTrend {
  date: string
  faithfulness: number
  answer_relevance: number
  context_precision: number
  overall_score: number
  query_count: number
}

export interface AgentPerformance {
  agent_name: string
  avg_duration_ms: number
  success_rate: number
  call_count: number
}

export interface AnalyticsDashboardResponse {
  total_queries: number
  avg_confidence: number
  documents_indexed: number
  active_sessions: number
  pass_rate: number
  evaluation_trends: EvaluationTrend[]
  agent_performance: AgentPerformance[]
  daily_queries: { date: string; count: number }[]
}

// Recommendations types
export interface LearningTopic {
  topic: string
  description: string
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  estimated_time_minutes: number
  tags: string[]
  relevance_score: number
  prerequisites: string[]
}

export interface RecommendationRequest {
  current_topic?: string
  skill_level?: 'beginner' | 'intermediate' | 'advanced'
  session_id?: string
}

export interface RecommendationResponse {
  recommendations: LearningTopic[]
  current_level: string
  next_milestone: string
}

// Notification type
export interface Notification {
  id: string
  type: 'success' | 'error' | 'info' | 'warning'
  message: string
  timestamp: number
}
