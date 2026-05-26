import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { History, MessageSquare, ChevronDown, ChevronUp, Trash2, Bot, User, RefreshCw, Clock } from 'lucide-react'
import api from '../services/api'
import { ConversationSession, ConversationMessage } from '../types'
import { useStore } from '../store/useStore'

const MOCK_SESSIONS: ConversationSession[] = [
  {
    session_id: 'sess_abc123def456',
    created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
    last_active: new Date(Date.now() - 3600000 * 3).toISOString(),
    message_count: 8,
    summary: 'Discussion about RAG architectures and vector embeddings',
    messages: [
      { role: 'user', content: 'What is retrieval augmented generation?', timestamp: new Date(Date.now() - 86400000 * 2).toISOString() },
      { role: 'assistant', content: 'Retrieval Augmented Generation (RAG) is a technique that combines retrieval-based and generative approaches...', timestamp: new Date(Date.now() - 86400000 * 2 + 2000).toISOString(), confidence_score: 0.92 },
      { role: 'user', content: 'How do vector embeddings work?', timestamp: new Date(Date.now() - 86400000 * 2 + 60000).toISOString() },
      { role: 'assistant', content: 'Vector embeddings are dense numerical representations of text that capture semantic meaning...', timestamp: new Date(Date.now() - 86400000 * 2 + 62000).toISOString(), confidence_score: 0.89 },
    ],
  },
  {
    session_id: 'sess_xyz789ghi012',
    created_at: new Date(Date.now() - 86400000).toISOString(),
    last_active: new Date(Date.now() - 1800000).toISOString(),
    message_count: 4,
    summary: 'Questions about multi-agent systems and LangChain',
    messages: [
      { role: 'user', content: 'Explain multi-agent systems in AI', timestamp: new Date(Date.now() - 86400000).toISOString() },
      { role: 'assistant', content: 'Multi-agent systems consist of multiple AI agents that collaborate to solve complex problems...', timestamp: new Date(Date.now() - 86400000 + 3000).toISOString(), confidence_score: 0.88 },
    ],
  },
  {
    session_id: 'sess_mno345pqr678',
    created_at: new Date(Date.now() - 3600000).toISOString(),
    last_active: new Date(Date.now() - 900000).toISOString(),
    message_count: 2,
    summary: 'Introduction to prompt engineering',
    messages: [
      { role: 'user', content: 'What are the best practices for prompt engineering?', timestamp: new Date(Date.now() - 3600000).toISOString() },
      { role: 'assistant', content: 'Prompt engineering involves crafting effective instructions for LLMs. Key practices include...', timestamp: new Date(Date.now() - 3600000 + 2500).toISOString(), confidence_score: 0.91 },
    ],
  },
]

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function MessageBubble({ message }: { message: ConversationMessage }) {
  const isUser = message.role === 'user'
  return (
    <div className={`flex items-end gap-2 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${
        isUser ? 'bg-indigo-600' : 'bg-gradient-to-br from-indigo-500 to-purple-600'
      }`}>
        {isUser ? <User className="w-3.5 h-3.5 text-white" /> : <Bot className="w-3.5 h-3.5 text-white" />}
      </div>
      <div className={`max-w-[80%] px-3 py-2 rounded-xl text-sm ${
        isUser
          ? 'bg-indigo-600 text-white rounded-br-sm'
          : 'dark:bg-gray-800 bg-gray-100 dark:text-gray-200 text-gray-800 rounded-bl-sm'
      }`}>
        <p className="leading-relaxed">{message.content}</p>
        <div className="flex items-center gap-2 mt-1">
          <span className={`text-xs opacity-60 flex items-center gap-1`}>
            <Clock className="w-2.5 h-2.5" />
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
          {message.confidence_score && (
            <span className="text-xs opacity-60">· {Math.round(message.confidence_score * 100)}% conf</span>
          )}
        </div>
      </div>
    </div>
  )
}

function SessionCard({ session, onDelete }: { session: ConversationSession; onDelete: (id: string) => void }) {
  const [expanded, setExpanded] = useState(false)
  const [loading, setLoading] = useState(false)
  const [fullSession, setFullSession] = useState<ConversationSession | null>(null)

  const handleExpand = async () => {
    if (!expanded && !fullSession) {
      setLoading(true)
      try {
        const full = await api.getSessionHistory(session.session_id)
        setFullSession(full)
      } catch {
        setFullSession(session)
      } finally {
        setLoading(false)
      }
    }
    setExpanded(!expanded)
  }

  const messages = (fullSession || session).messages

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl dark:bg-gray-900 bg-white border dark:border-gray-800 border-gray-200 overflow-hidden"
    >
      <div className="flex items-center gap-4 p-5">
        <div className="w-12 h-12 rounded-xl bg-indigo-600/20 flex items-center justify-center flex-shrink-0">
          <MessageSquare className="w-6 h-6 text-indigo-500" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium dark:text-white text-gray-900 truncate">
            {session.summary || `Session ${session.session_id.slice(5, 13)}`}
          </p>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-xs dark:text-gray-500 text-gray-400 flex items-center gap-1">
              <MessageSquare className="w-3 h-3" /> {session.message_count} messages
            </span>
            <span className="text-xs dark:text-gray-500 text-gray-400 flex items-center gap-1">
              <Clock className="w-3 h-3" /> {timeAgo(session.last_active)}
            </span>
            <span className="text-xs font-mono dark:text-gray-600 text-gray-400">
              {session.session_id.slice(0, 16)}...
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onDelete(session.session_id)}
            className="p-2 text-red-400 hover:text-red-300 dark:hover:bg-red-400/10 hover:bg-red-50 rounded-xl transition-all"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          <button
            onClick={handleExpand}
            className="p-2 dark:text-gray-400 text-gray-600 dark:hover:bg-gray-800 hover:bg-gray-100 rounded-xl transition-all"
          >
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-t dark:border-gray-800 border-gray-200"
          >
            <div className="p-5 space-y-3 max-h-96 overflow-y-auto">
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="w-5 h-5 text-indigo-500 animate-spin" />
                </div>
              ) : messages.length === 0 ? (
                <p className="text-center dark:text-gray-500 text-gray-400 py-8 text-sm">No messages found</p>
              ) : (
                messages.map((msg, i) => (
                  <MessageBubble key={i} message={msg} />
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default function HistoryPage() {
  const { addNotification } = useStore()
  const [sessions, setSessions] = useState<ConversationSession[]>([])
  const [loading, setLoading] = useState(true)

  const loadSessions = async () => {
    setLoading(true)
    try {
      const data = await api.getHistory()
      setSessions(data)
    } catch {
      setSessions(MOCK_SESSIONS)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadSessions() }, [])

  const handleDelete = async (sessionId: string) => {
    try {
      await api.deleteSession(sessionId)
      setSessions(prev => prev.filter(s => s.session_id !== sessionId))
      addNotification('success', 'Session deleted')
    } catch (err: any) {
      addNotification('error', err.message)
    }
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold dark:text-white text-gray-900 flex items-center gap-3">
            <History className="w-8 h-8 text-indigo-500" /> Conversation History
          </h1>
          <p className="dark:text-gray-400 text-gray-500 mt-1">Browse and review past learning sessions</p>
        </div>
        <button onClick={loadSessions}
          className="p-2 dark:bg-gray-800 bg-white dark:hover:bg-gray-700 hover:bg-gray-100 border dark:border-gray-700 border-gray-200 rounded-xl transition-colors">
          <RefreshCw className={`w-4 h-4 dark:text-gray-400 text-gray-600 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </motion.div>

      {/* Stats */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1, transition: { delay: 0.1 } }}
        className="grid grid-cols-3 gap-4 mb-8">
        {[
          { label: 'Total Sessions', value: sessions.length },
          { label: 'Total Messages', value: sessions.reduce((s, c) => s + c.message_count, 0) },
          { label: 'Active Today', value: sessions.filter(s => Date.now() - new Date(s.last_active).getTime() < 86400000).length },
        ].map((stat, i) => (
          <div key={stat.label} className="rounded-2xl p-4 dark:bg-gray-900 bg-white border dark:border-gray-800 border-gray-200 text-center">
            <p className="text-2xl font-bold dark:text-white text-gray-900">{stat.value}</p>
            <p className="text-sm dark:text-gray-400 text-gray-500">{stat.label}</p>
          </div>
        ))}
      </motion.div>

      {/* Sessions list */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-24 dark:bg-gray-800 bg-gray-200 rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : sessions.length === 0 ? (
        <div className="text-center py-20">
          <History className="w-16 h-16 mx-auto mb-4 dark:text-gray-700 text-gray-300" />
          <h3 className="text-lg font-medium dark:text-white text-gray-900 mb-2">No History Yet</h3>
          <p className="dark:text-gray-500 text-gray-400 text-sm">Start a conversation in the Chat page to build your history</p>
        </div>
      ) : (
        <div className="space-y-4">
          {sessions.map((session, i) => (
            <motion.div key={session.session_id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0, transition: { delay: i * 0.08 } }}>
              <SessionCard session={session} onDelete={handleDelete} />
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
