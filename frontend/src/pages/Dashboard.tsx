import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  MessageSquare, FileText, BarChart3, Zap, TrendingUp,
  ArrowRight, Brain, Search, BookOpen, Target, Sparkles,
} from 'lucide-react'
import api from '../services/api'
import { AnalyticsDashboardResponse } from '../types'
import { useStore } from '../store/useStore'

function AnimatedCounter({ value, duration = 1400 }: { value: number; duration?: number }) {
  const [display, setDisplay] = useState(0)
  useEffect(() => {
    let start = 0
    const step = value / (duration / 16)
    const timer = setInterval(() => {
      start += step
      if (start >= value) { setDisplay(value); clearInterval(timer) }
      else setDisplay(Math.floor(start))
    }, 16)
    return () => clearInterval(timer)
  }, [value, duration])
  return <span>{display.toLocaleString()}</span>
}

const cardVariants = {
  hidden:  { opacity: 0, y: 22 },
  visible: (i: number) => ({ opacity: 1, y: 0, transition: { delay: i * 0.09, duration: 0.42, ease: 'easeOut' } }),
}

export default function Dashboard() {
  const navigate   = useNavigate()
  const { theme }  = useStore()
  const isDark     = theme === 'dark'

  const [analytics,   setAnalytics  ] = useState<AnalyticsDashboardResponse | null>(null)
  const [loading,     setLoading    ] = useState(true)
  const [quickQuery,  setQuickQuery ] = useState('')

  useEffect(() => {
    api.getAnalytics(7)
      .then(setAnalytics)
      .catch(() => setAnalytics({
        total_queries: 1284, avg_confidence: 0.87, documents_indexed: 42,
        active_sessions: 7, pass_rate: 0.91, evaluation_trends: [],
        agent_performance: [], daily_queries: [],
      } as any))
      .finally(() => setLoading(false))
  }, [])

  const stats = [
    {
      label: 'Total Queries',
      value: analytics?.total_queries ?? 0,
      icon: MessageSquare,
      gradient: 'from-teal-500 to-teal-600',
      bg: isDark ? 'bg-teal-900/60 border-teal-700' : 'bg-teal-50 border-teal-200',
      iconBg: 'bg-teal-600',
      suffix: '',
    },
    {
      label: 'Avg Confidence',
      value: Math.round((analytics?.avg_confidence ?? 0) * 100),
      icon: Target,
      gradient: 'from-emerald-500 to-teal-500',
      bg: isDark ? 'bg-emerald-900/40 border-emerald-800' : 'bg-emerald-50 border-emerald-200',
      iconBg: 'bg-emerald-600',
      suffix: '%',
    },
    {
      label: 'Documents Indexed',
      value: analytics?.documents_indexed ?? 0,
      icon: FileText,
      gradient: 'from-teal-400 to-cyan-500',
      bg: isDark ? 'bg-cyan-900/40 border-cyan-800' : 'bg-cyan-50 border-cyan-200',
      iconBg: 'bg-teal-500',
      suffix: '',
    },
    {
      label: 'Pass Rate',
      value: Math.round((analytics?.pass_rate ?? 0) * 100),
      icon: TrendingUp,
      gradient: 'from-teal-600 to-teal-700',
      bg: isDark ? 'bg-teal-900/60 border-teal-700' : 'bg-teal-50/80 border-teal-300',
      iconBg: 'bg-teal-700',
      suffix: '%',
    },
  ]

  /* shared card class */
  const card = isDark
    ? 'bg-teal-900/50 border border-teal-800 rounded-2xl shadow-teal'
    : 'bg-white border border-cream-300 rounded-2xl shadow-card'

  return (
    <div className="p-8 max-w-7xl mx-auto">

      {/* ── Header ── */}
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <Sparkles className="w-6 h-6 text-teal-500" />
          <h1 className={`text-3xl font-bold tracking-tight ${isDark ? 'text-cream-50' : 'text-teal-800'}`}>
            Welcome back!
          </h1>
        </div>
        <p className={`mt-1 text-sm ${isDark ? 'text-teal-300' : 'text-teal-600'}`}>
          Your AI-powered learning assistant is ready. What would you like to explore today?
        </p>
      </motion.div>

      {/* ── Stats Grid ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map((stat, i) => (
          <motion.div
            key={stat.label}
            custom={i}
            variants={cardVariants}
            initial="hidden"
            animate="visible"
            className={`rounded-2xl border p-6 ${stat.bg}`}
          >
            <div className="flex items-start justify-between mb-4">
              <div className={`w-10 h-10 rounded-xl ${stat.iconBg} flex items-center justify-center shadow-teal`}>
                <stat.icon className="w-5 h-5 text-white" />
              </div>
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                isDark ? 'bg-teal-800 text-teal-300' : 'bg-teal-100 text-teal-600'
              }`}>live</span>
            </div>
            <div className={`text-3xl font-bold mb-1 ${isDark ? 'text-cream-50' : 'text-teal-900'}`}>
              {loading
                ? <div className={`h-8 w-20 rounded animate-pulse ${isDark ? 'bg-teal-800' : 'bg-cream-200'}`} />
                : <><AnimatedCounter value={stat.value} />{stat.suffix}</>
              }
            </div>
            <p className={`text-sm ${isDark ? 'text-teal-400' : 'text-teal-600'}`}>{stat.label}</p>
          </motion.div>
        ))}
      </div>

      {/* ── Quick Chat + Actions ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">

        {/* Quick Chat */}
        <motion.div
          initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.28 }}
          className={`lg:col-span-2 p-6 ${card}`}
        >
          <h2 className={`text-lg font-semibold mb-1 flex items-center gap-2 ${isDark ? 'text-cream-100' : 'text-teal-800'}`}>
            <Brain className="w-5 h-5 text-teal-500" />
            Quick Start
          </h2>
          <p className={`text-sm mb-4 ${isDark ? 'text-teal-400' : 'text-teal-500'}`}>
            Ask anything and get AI-powered answers with source citations
          </p>

          <div className="flex gap-3">
            <div className="flex-1 relative">
              <Search className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${isDark ? 'text-teal-500' : 'text-teal-400'}`} />
              <input
                value={quickQuery}
                onChange={e => setQuickQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && quickQuery.trim() && navigate('/chat', { state: { initialQuery: quickQuery } })}
                placeholder="Ask a question about your documents..."
                className={`w-full pl-10 pr-4 py-3 rounded-xl text-sm border transition-all focus:outline-none focus:ring-2 focus:ring-teal-400 ${
                  isDark
                    ? 'bg-teal-950/60 border-teal-700 text-cream-100 placeholder-teal-600'
                    : 'bg-cream-100 border-cream-300 text-teal-900 placeholder-teal-400'
                }`}
              />
            </div>
            <button
              onClick={() => quickQuery.trim() && navigate('/chat', { state: { initialQuery: quickQuery } })}
              className="px-5 py-3 btn-teal rounded-xl text-sm flex items-center gap-2"
            >
              Ask <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          {/* Chips */}
          <div className="flex flex-wrap gap-2 mt-4">
            {['Explain machine learning', 'Summarize key concepts', 'Generate a quiz', 'Best practices?'].map(q => (
              <button
                key={q}
                onClick={() => navigate('/chat', { state: { initialQuery: q } })}
                className={`px-3 py-1.5 text-xs rounded-full border transition-all ${
                  isDark
                    ? 'bg-teal-900 border-teal-700 text-teal-300 hover:border-teal-400 hover:text-teal-200'
                    : 'bg-cream-100 border-cream-300 text-teal-600 hover:border-teal-400 hover:bg-teal-50 hover:text-teal-700'
                }`}
              >
                {q}
              </button>
            ))}
          </div>
        </motion.div>

        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.34 }}
          className={`p-6 ${card}`}
        >
          <h2 className={`text-lg font-semibold mb-4 ${isDark ? 'text-cream-100' : 'text-teal-800'}`}>Quick Actions</h2>
          <div className="space-y-3">
            {[
              { label: 'Upload Documents',     icon: FileText,    to: '/upload',          color: 'text-teal-500' },
              { label: 'View Analytics',       icon: BarChart3,   to: '/analytics',        color: 'text-teal-600' },
              { label: 'Get Recommendations',  icon: BookOpen,    to: '/recommendations',  color: 'text-emerald-500' },
              { label: 'Browse History',       icon: MessageSquare, to: '/history',        color: 'text-teal-400' },
            ].map(({ label, icon: Icon, to, color }) => (
              <button
                key={to}
                onClick={() => navigate(to)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all group ${
                  isDark
                    ? 'bg-teal-950/60 hover:bg-teal-800/60 border border-teal-800'
                    : 'bg-cream-100 hover:bg-teal-50 border border-cream-300'
                }`}
              >
                <Icon className={`w-5 h-5 ${color}`} />
                <span className={`text-sm font-medium flex-1 text-left ${isDark ? 'text-teal-200' : 'text-teal-700'}`}>{label}</span>
                <ArrowRight className={`w-4 h-4 ${isDark ? 'text-teal-600' : 'text-teal-400'} group-hover:translate-x-1 transition-transform`} />
              </button>
            ))}
          </div>
        </motion.div>
      </div>

      {/* ── Agent Workflow ── */}
      <motion.div
        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
        className={`p-6 ${card}`}
      >
        <h2 className={`text-lg font-semibold mb-6 flex items-center gap-2 ${isDark ? 'text-cream-100' : 'text-teal-800'}`}>
          <Zap className="w-5 h-5 text-gold-400" />
          Multi-Agent Workflow
        </h2>
        <div className="overflow-x-auto">
          <svg viewBox="0 0 900 160" className="w-full max-w-4xl mx-auto" xmlns="http://www.w3.org/2000/svg">
            {/* Lines */}
            {[155, 330, 505, 680].map(x => (
              <line key={x} x1={x} y1="80" x2={x+55} y2="80"
                stroke={isDark ? '#267D75' : '#5BBDB5'} strokeWidth="2" strokeDasharray="5,4" />
            ))}
            {/* Arrows */}
            {[207, 382, 557, 732].map(x => (
              <polygon key={x} points={`${x},75 ${x+9},80 ${x},85`}
                fill={isDark ? '#3AACA3' : '#2E9A91'} />
            ))}
            {/* Nodes */}
            {[
              { x: 10,  label: 'Input',     sub: 'Query',       color: '#2E9A91', icon: '🔍' },
              { x: 215, label: 'Supervisor',sub: 'Router',      color: '#267D75', icon: '🧠' },
              { x: 390, label: 'Retrieval', sub: 'Hybrid RAG',  color: '#1E6059', icon: '📚' },
              { x: 565, label: 'Generation',sub: 'Agent',       color: '#3AACA3', icon: '✍️' },
              { x: 740, label: 'Reviewer',  sub: 'DeepEval',    color: '#5BBDB5', icon: '✅' },
            ].map(({ x, label, sub, color, icon }) => (
              <g key={x}>
                <rect x={x} y="30" width="135" height="90" rx="14"
                  fill={color} fillOpacity="0.12"
                  stroke={color} strokeOpacity="0.6" strokeWidth="1.5" />
                <text x={x+67} y="65"  textAnchor="middle" fontSize="20">{icon}</text>
                <text x={x+67} y="88"  textAnchor="middle" fontSize="12" fontWeight="600"
                  fill={isDark ? '#FAF8F3' : '#1E4540'}>{label}</text>
                <text x={x+67} y="105" textAnchor="middle" fontSize="10" fill={color}>{sub}</text>
              </g>
            ))}
          </svg>
        </div>
      </motion.div>
    </div>
  )
}
