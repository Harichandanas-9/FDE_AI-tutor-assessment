import { useState, useEffect, useRef, useCallback } from 'react'
import { useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Send, Bot, User, ChevronDown, ChevronUp, BookOpen,
  Zap, Clock, CheckCircle, XCircle, Hash, AlertCircle
} from 'lucide-react'
import api from '../services/api'
import { ChatResponse, ConversationMessage, SourceReference, AgentTrace, EvaluationMetrics } from '../types'
import { useStore } from '../store/useStore'

type Mode = 'chat' | 'explain' | 'summarize' | 'notes'

interface Message extends ConversationMessage {
  id: string
  response?: ChatResponse
  isLoading?: boolean
}

function ConfidenceBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color = pct >= 80 ? 'text-green-400 bg-green-400/10 border-green-400/30'
    : pct >= 60 ? 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30'
    : 'text-red-400 bg-red-400/10 border-red-400/30'
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border ${color}`}>
      <Zap className="w-3 h-3" /> {pct}% confidence
    </span>
  )
}

function SourcesPanel({ sources }: { sources: SourceReference[] }) {
  const [open, setOpen] = useState(false)
  if (!sources.length) return null
  return (
    <div className="mt-3">
      <button onClick={() => setOpen(!open)} className="flex items-center gap-2 text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
        <BookOpen className="w-3.5 h-3.5" />
        {sources.length} source{sources.length > 1 ? 's' : ''}
        {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden mt-2 space-y-2">
            {sources.map((src, i) => (
              <div key={i} className="p-3 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-xs">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-indigo-400">{src.document_name}</span>
                  {src.page_number && <span className="text-gray-500">p. {src.page_number}</span>}
                </div>
                <p className="dark:text-gray-400 text-gray-500 line-clamp-2">{src.chunk_text}</p>
                <div className="mt-1 text-indigo-500">Relevance: {Math.round(src.relevance_score * 100)}%</div>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function AgentTracePanel({ traces }: { traces: AgentTrace[] }) {
  const [open, setOpen] = useState(false)
  if (!traces.length) return null
  return (
    <div className="mt-2">
      <button onClick={() => setOpen(!open)} className="flex items-center gap-2 text-xs text-purple-400 hover:text-purple-300 transition-colors">
        <Hash className="w-3.5 h-3.5" />
        Agent trace ({traces.length} steps)
        {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden mt-2 space-y-1.5">
            {traces.map((t, i) => (
              <div key={i} className="flex items-start gap-2 p-2 rounded-lg dark:bg-gray-800 bg-gray-100 text-xs">
                {t.status === 'success' ? <CheckCircle className="w-3.5 h-3.5 text-green-400 mt-0.5 flex-shrink-0" />
                  : t.status === 'error' ? <XCircle className="w-3.5 h-3.5 text-red-400 mt-0.5 flex-shrink-0" />
                  : <AlertCircle className="w-3.5 h-3.5 text-gray-400 mt-0.5 flex-shrink-0" />}
                <div>
                  <span className="font-medium text-purple-400">{t.agent_name}</span>
                  <span className="dark:text-gray-400 text-gray-500"> → {t.action}</span>
                  <span className="ml-2 dark:text-gray-600 text-gray-400 flex items-center gap-1 inline-flex">
                    <Clock className="w-3 h-3" />{t.duration_ms}ms
                  </span>
                </div>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function EvalMetricsBar({ metrics }: { metrics: EvaluationMetrics }) {
  const bars = [
    { label: 'Faithfulness', value: metrics.faithfulness },
    { label: 'Relevance', value: metrics.answer_relevance },
    { label: 'Precision', value: metrics.context_precision },
  ]
  return (
    <div className="mt-3 p-3 rounded-lg dark:bg-gray-800/50 bg-gray-100 border dark:border-gray-700 border-gray-200">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium dark:text-gray-400 text-gray-500">Evaluation Metrics</span>
        <span className={`text-xs px-2 py-0.5 rounded-full ${metrics.pass_fail === 'pass' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
          {metrics.pass_fail.toUpperCase()}
        </span>
      </div>
      {bars.map(({ label, value }) => (
        <div key={label} className="mb-1.5">
          <div className="flex justify-between text-xs mb-0.5">
            <span className="dark:text-gray-500 text-gray-400">{label}</span>
            <span className="dark:text-gray-400 text-gray-600">{Math.round(value * 100)}%</span>
          </div>
          <div className="h-1 dark:bg-gray-700 bg-gray-300 rounded-full overflow-hidden">
            <motion.div initial={{ width: 0 }} animate={{ width: `${value * 100}%` }} transition={{ duration: 0.8, delay: 0.2 }}
              className={`h-full rounded-full ${value >= 0.8 ? 'bg-green-500' : value >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'}`} />
          </div>
        </div>
      ))}
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex items-end gap-3 mb-4">
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0">
        <Bot className="w-4 h-4 text-white" />
      </div>
      <div className="px-4 py-3 rounded-2xl rounded-bl-sm dark:bg-gray-800 bg-gray-200">
        <div className="flex gap-1">
          {[0, 0.2, 0.4].map((d, i) => (
            <motion.div key={i} className="w-2 h-2 rounded-full bg-indigo-500"
              animate={{ y: [0, -6, 0] }} transition={{ duration: 0.6, delay: d, repeat: Infinity }} />
          ))}
        </div>
      </div>
    </div>
  )
}

const modeOptions: { value: Mode; label: string; emoji: string }[] = [
  { value: 'chat', label: 'Chat', emoji: '💬' },
  { value: 'explain', label: 'Explain', emoji: '📖' },
  { value: 'summarize', label: 'Summarize', emoji: '📝' },
  { value: 'notes', label: 'Notes', emoji: '📋' },
]

export default function ChatPage() {
  const location = useLocation()
  const { addNotification, currentSessionId, setSessionId } = useStore()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [mode, setMode] = useState<Mode>('chat')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (location.state?.initialQuery) {
      setInput(location.state.initialQuery)
      setTimeout(() => handleSend(location.state.initialQuery), 300)
    }
  }, [])

  const handleSend = useCallback(async (overrideQuery?: string) => {
    const query = overrideQuery ?? input.trim()
    if (!query || isLoading) return
    setInput('')
    setIsLoading(true)

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    }
    const loadingMsg: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isLoading: true,
    }
    setMessages(prev => [...prev, userMsg, loadingMsg])

    try {
      const response = await api.sendChat({
        query,
        session_id: currentSessionId ?? undefined,
        mode,
      })
      setSessionId(response.session_id)
      setMessages(prev => prev.map(m =>
        m.id === loadingMsg.id ? {
          ...m,
          content: response.answer,
          isLoading: false,
          confidence_score: response.confidence_score,
          response,
        } : m
      ))
    } catch (err: any) {
      addNotification('error', err.message || 'Failed to get response')
      setMessages(prev => prev.filter(m => m.id !== loadingMsg.id))
    } finally {
      setIsLoading(false)
    }
  }, [input, isLoading, mode, currentSessionId])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="flex-shrink-0 px-6 py-4 border-b dark:border-gray-800 border-gray-200 dark:bg-gray-900 bg-white">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold dark:text-white text-gray-900 flex items-center gap-2">
              <Bot className="w-5 h-5 text-indigo-500" /> AI Learning Assistant
            </h1>
            {currentSessionId && (
              <p className="text-xs dark:text-gray-500 text-gray-400 mt-0.5 font-mono">
                Session: {currentSessionId.slice(0, 16)}...
              </p>
            )}
          </div>
          {/* Mode selector */}
          <div className="flex gap-1 p-1 rounded-xl dark:bg-gray-800 bg-gray-100">
            {modeOptions.map(opt => (
              <button
                key={opt.value}
                onClick={() => setMode(opt.value)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  mode === opt.value
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'dark:text-gray-400 text-gray-600 dark:hover:text-white hover:text-gray-900'
                }`}
              >
                {opt.emoji} {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mb-4 shadow-2xl shadow-indigo-500/30">
              <Bot className="w-10 h-10 text-white" />
            </div>
            <h2 className="text-xl font-semibold dark:text-white text-gray-900 mb-2">Start a Conversation</h2>
            <p className="dark:text-gray-400 text-gray-500 max-w-sm text-sm">
              Ask questions about your uploaded documents. I'll provide answers with confidence scores and source citations.
            </p>
          </div>
        )}

        <AnimatePresence>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex items-end gap-3 mb-6 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
            >
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                msg.role === 'user'
                  ? 'bg-indigo-600'
                  : 'bg-gradient-to-br from-indigo-500 to-purple-600'
              }`}>
                {msg.role === 'user' ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-white" />}
              </div>
              <div className={`max-w-[75%] ${msg.role === 'user' ? 'items-end' : 'items-start'} flex flex-col`}>
                {msg.isLoading ? (
                  <TypingIndicator />
                ) : (
                  <div className={`px-4 py-3 rounded-2xl text-sm ${
                    msg.role === 'user'
                      ? 'bg-indigo-600 text-white rounded-br-sm'
                      : 'dark:bg-gray-800 bg-gray-200 dark:text-gray-100 text-gray-800 rounded-bl-sm'
                  }`}>
                    <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                    {msg.role === 'assistant' && msg.response && (
                      <>
                        <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t dark:border-gray-700 border-gray-300">
                          <ConfidenceBadge score={msg.response.confidence_score} />
                          <span className="text-xs dark:text-gray-500 text-gray-400 flex items-center gap-1">
                            <Clock className="w-3 h-3" />{msg.response.processing_time_ms}ms
                          </span>
                        </div>
                        <EvalMetricsBar metrics={msg.response.evaluation_metrics} />
                        <SourcesPanel sources={msg.response.sources} />
                        <AgentTracePanel traces={msg.response.agent_traces} />
                        {msg.response.follow_up_topics.length > 0 && (
                          <div className="mt-3 pt-3 border-t dark:border-gray-700 border-gray-300">
                            <p className="text-xs dark:text-gray-500 text-gray-400 mb-2">Follow-up topics:</p>
                            <div className="flex flex-wrap gap-1.5">
                              {msg.response.follow_up_topics.map(t => (
                                <button key={t} onClick={() => setInput(t)}
                                  className="px-2.5 py-1 text-xs rounded-full dark:bg-indigo-900/30 bg-indigo-100 text-indigo-400 dark:hover:bg-indigo-900/50 hover:bg-indigo-200 transition-colors border dark:border-indigo-800 border-indigo-200">
                                  {t}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}
                <span className="text-xs dark:text-gray-600 text-gray-400 mt-1 px-1">
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </span>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="flex-shrink-0 p-4 border-t dark:border-gray-800 border-gray-200 dark:bg-gray-900 bg-white">
        <div className="flex gap-3 items-end max-w-4xl mx-auto">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question... (Enter to send, Shift+Enter for new line)"
              rows={1}
              style={{ minHeight: '44px', maxHeight: '120px' }}
              className="w-full px-4 py-3 rounded-xl dark:bg-gray-800 bg-gray-100 dark:text-white text-gray-900 dark:placeholder-gray-500 placeholder-gray-400 border dark:border-gray-700 border-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm resize-none"
              onInput={e => {
                const t = e.currentTarget
                t.style.height = 'auto'
                t.style.height = Math.min(t.scrollHeight, 120) + 'px'
              }}
            />
          </div>
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isLoading}
            className="w-11 h-11 flex items-center justify-center bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl transition-colors flex-shrink-0"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  )
}
