import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  LineChart, Line, BarChart, Bar, RadarChart, Radar, PolarGrid,
  PolarAngleAxis, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, PolarRadiusAxis
} from 'recharts'
import { TrendingUp, MessageSquare, CheckCircle, XCircle, RefreshCw, BarChart3 } from 'lucide-react'
import api from '../services/api'
import { AnalyticsDashboardResponse } from '../types'

const MOCK_ANALYTICS: AnalyticsDashboardResponse = {
  total_queries: 1284,
  avg_confidence: 0.87,
  documents_indexed: 42,
  active_sessions: 7,
  pass_rate: 0.91,
  evaluation_trends: Array.from({ length: 7 }, (_, i) => {
    const d = new Date(); d.setDate(d.getDate() - (6 - i))
    return {
      date: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      faithfulness: 0.78 + Math.random() * 0.15,
      answer_relevance: 0.80 + Math.random() * 0.12,
      context_precision: 0.75 + Math.random() * 0.18,
      overall_score: 0.79 + Math.random() * 0.14,
      query_count: Math.floor(80 + Math.random() * 120),
    }
  }),
  agent_performance: [
    { agent_name: 'Router Agent', avg_duration_ms: 45, success_rate: 0.99, call_count: 1284 },
    { agent_name: 'Retrieval Agent', avg_duration_ms: 320, success_rate: 0.96, call_count: 1102 },
    { agent_name: 'Synthesis Agent', avg_duration_ms: 1240, success_rate: 0.94, call_count: 1102 },
    { agent_name: 'Evaluator Agent', avg_duration_ms: 280, success_rate: 0.98, call_count: 1098 },
    { agent_name: 'Quiz Agent', avg_duration_ms: 890, success_rate: 0.92, call_count: 340 },
  ],
  daily_queries: Array.from({ length: 7 }, (_, i) => {
    const d = new Date(); d.setDate(d.getDate() - (6 - i))
    return { date: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }), count: Math.floor(80 + Math.random() * 120) }
  }),
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-3 shadow-xl">
        <p className="text-gray-400 text-xs mb-2">{label}</p>
        {payload.map((p: any) => (
          <p key={p.dataKey} className="text-sm" style={{ color: p.color }}>
            {p.name}: {typeof p.value === 'number' && p.value < 2 ? Math.round(p.value * 100) + '%' : p.value}
          </p>
        ))}
      </div>
    )
  }
  return null
}

const COLORS = {
  faithfulness: '#6366f1',
  answer_relevance: '#10b981',
  context_precision: '#f59e0b',
  overall_score: '#8b5cf6',
}

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsDashboardResponse>(MOCK_ANALYTICS)
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState(7)
  const [refreshing, setRefreshing] = useState(false)

  const loadData = async (d = days, showRefresh = false) => {
    if (showRefresh) setRefreshing(true)
    else setLoading(true)
    try {
      const result = await api.getAnalytics(d)
      setData(result)
    } catch {
      setData(MOCK_ANALYTICS)
    } finally {
      setLoading(false); setRefreshing(false)
    }
  }

  useEffect(() => { loadData() }, [days])

  const radarData = data.agent_performance.map(a => ({
    agent: a.agent_name.replace(' Agent', ''),
    'Success Rate': Math.round(a.success_rate * 100),
    'Speed Score': Math.max(10, 100 - Math.round(a.avg_duration_ms / 20)),
  }))

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold dark:text-white text-gray-900">Analytics</h1>
          <p className="dark:text-gray-400 text-gray-500 mt-1">Performance metrics and evaluation trends</p>
        </div>
        <div className="flex items-center gap-3">
          <select value={days} onChange={e => setDays(Number(e.target.value))}
            className="px-4 py-2 rounded-xl dark:bg-gray-800 bg-white dark:text-white text-gray-900 border dark:border-gray-700 border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
          </select>
          <button onClick={() => loadData(days, true)}
            className="p-2 dark:bg-gray-800 bg-white dark:hover:bg-gray-700 hover:bg-gray-100 border dark:border-gray-700 border-gray-200 rounded-xl transition-colors">
            <RefreshCw className={`w-4 h-4 dark:text-gray-400 text-gray-600 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </motion.div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[
          { label: 'Total Queries', value: data.total_queries.toLocaleString(), icon: MessageSquare, color: 'text-blue-500', bg: 'bg-blue-500/10' },
          { label: 'Avg Confidence', value: Math.round(data.avg_confidence * 100) + '%', icon: TrendingUp, color: 'text-green-500', bg: 'bg-green-500/10' },
          { label: 'Pass Rate', value: Math.round(data.pass_rate * 100) + '%', icon: CheckCircle, color: 'text-indigo-500', bg: 'bg-indigo-500/10' },
          { label: 'Fail Rate', value: Math.round((1 - data.pass_rate) * 100) + '%', icon: XCircle, color: 'text-red-500', bg: 'bg-red-500/10' },
        ].map((s, i) => (
          <motion.div key={s.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0, transition: { delay: i * 0.1 } }}
            className={`rounded-2xl p-5 border dark:border-gray-800 border-gray-200 dark:bg-gray-900 bg-white`}>
            <div className={`w-10 h-10 rounded-xl ${s.bg} flex items-center justify-center mb-3`}>
              <s.icon className={`w-5 h-5 ${s.color}`} />
            </div>
            {loading ? <div className="h-8 w-24 dark:bg-gray-700 bg-gray-200 rounded animate-pulse" />
              : <p className="text-2xl font-bold dark:text-white text-gray-900">{s.value}</p>}
            <p className="text-sm dark:text-gray-400 text-gray-500 mt-1">{s.label}</p>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Evaluation Trends Line Chart */}
        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0, transition: { delay: 0.3 } }}
          className="rounded-2xl p-6 dark:bg-gray-900 bg-white border dark:border-gray-800 border-gray-200">
          <h2 className="text-lg font-semibold dark:text-white text-gray-900 mb-6 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-indigo-500" /> Evaluation Trends
          </h2>
          {loading ? <div className="h-64 dark:bg-gray-800 bg-gray-100 rounded-xl animate-pulse" /> : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={data.evaluation_trends} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.5} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#9ca3af' }} />
                <YAxis domain={[0.5, 1]} tickFormatter={v => `${Math.round(v * 100)}%`} tick={{ fontSize: 11, fill: '#9ca3af' }} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
                {Object.entries(COLORS).map(([key, color]) => (
                  <Line key={key} type="monotone" dataKey={key} stroke={color} strokeWidth={2}
                    dot={{ r: 3, fill: color }} name={key.replace('_', ' ')} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </motion.div>

        {/* Daily Queries Bar Chart */}
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0, transition: { delay: 0.35 } }}
          className="rounded-2xl p-6 dark:bg-gray-900 bg-white border dark:border-gray-800 border-gray-200">
          <h2 className="text-lg font-semibold dark:text-white text-gray-900 mb-6 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-purple-500" /> Daily Queries
          </h2>
          {loading ? <div className="h-64 dark:bg-gray-800 bg-gray-100 rounded-xl animate-pulse" /> : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.daily_queries} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.5} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#9ca3af' }} />
                <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="count" name="Queries" fill="#6366f1" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Radar Chart - Agent Performance */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0, transition: { delay: 0.4 } }}
          className="rounded-2xl p-6 dark:bg-gray-900 bg-white border dark:border-gray-800 border-gray-200">
          <h2 className="text-lg font-semibold dark:text-white text-gray-900 mb-6">Agent Performance Radar</h2>
          {loading ? <div className="h-64 dark:bg-gray-800 bg-gray-100 rounded-xl animate-pulse" /> : (
            <ResponsiveContainer width="100%" height={260}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="#374151" />
                <PolarAngleAxis dataKey="agent" tick={{ fontSize: 11, fill: '#9ca3af' }} />
                <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 9, fill: '#6b7280' }} />
                <Radar name="Success Rate" dataKey="Success Rate" stroke="#6366f1" fill="#6366f1" fillOpacity={0.25} />
                <Radar name="Speed Score" dataKey="Speed Score" stroke="#10b981" fill="#10b981" fillOpacity={0.25} />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
                <Tooltip content={<CustomTooltip />} />
              </RadarChart>
            </ResponsiveContainer>
          )}
        </motion.div>

        {/* Agent Performance Table */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0, transition: { delay: 0.45 } }}
          className="rounded-2xl p-6 dark:bg-gray-900 bg-white border dark:border-gray-800 border-gray-200">
          <h2 className="text-lg font-semibold dark:text-white text-gray-900 mb-6">Agent Performance Details</h2>
          {loading ? (
            <div className="space-y-3">{[1,2,3,4,5].map(i => <div key={i} className="h-12 dark:bg-gray-800 bg-gray-100 rounded-xl animate-pulse" />)}</div>
          ) : (
            <div className="space-y-3">
              {data.agent_performance.map((agent, i) => (
                <motion.div key={agent.agent_name} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0, transition: { delay: 0.5 + i * 0.05 } }}
                  className="flex items-center gap-4 p-3 rounded-xl dark:bg-gray-800 bg-gray-100">
                  <div className="flex-1">
                    <p className="text-sm font-medium dark:text-white text-gray-900">{agent.agent_name}</p>
                    <p className="text-xs dark:text-gray-500 text-gray-400">{agent.call_count.toLocaleString()} calls · {agent.avg_duration_ms}ms avg</p>
                  </div>
                  <div className="text-right">
                    <p className={`text-sm font-bold ${agent.success_rate >= 0.95 ? 'text-green-400' : agent.success_rate >= 0.9 ? 'text-yellow-400' : 'text-red-400'}`}>
                      {Math.round(agent.success_rate * 100)}%
                    </p>
                    <p className="text-xs dark:text-gray-500 text-gray-400">success</p>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}
