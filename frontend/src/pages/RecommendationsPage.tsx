import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Lightbulb, Clock, Tag, ChevronRight, RefreshCw, BookOpen } from 'lucide-react'
import api from '../services/api'
import { LearningTopic, RecommendationResponse } from '../types'
import { useStore } from '../store/useStore'

const MOCK_RECOMMENDATIONS: RecommendationResponse = {
  current_level: 'intermediate',
  next_milestone: 'Advanced RAG Architectures',
  recommendations: [
    {
      topic: 'Vector Embeddings Fundamentals',
      description: 'Understand how text is converted to vector representations and why similarity search works. Learn about embedding models like sentence-transformers.',
      difficulty: 'beginner',
      estimated_time_minutes: 30,
      tags: ['embeddings', 'NLP', 'mathematics'],
      relevance_score: 0.95,
      prerequisites: [],
    },
    {
      topic: 'RAG Architecture Patterns',
      description: 'Explore different patterns for retrieval-augmented generation including naive RAG, advanced RAG, and modular RAG approaches.',
      difficulty: 'intermediate',
      estimated_time_minutes: 60,
      tags: ['RAG', 'architecture', 'LLM'],
      relevance_score: 0.92,
      prerequisites: ['Vector Embeddings Fundamentals'],
    },
    {
      topic: 'Multi-Agent Systems Design',
      description: 'Learn how to orchestrate multiple AI agents for complex tasks, including agent communication, tool use, and workflow orchestration.',
      difficulty: 'advanced',
      estimated_time_minutes: 90,
      tags: ['agents', 'orchestration', 'LangChain'],
      relevance_score: 0.89,
      prerequisites: ['RAG Architecture Patterns', 'LLM Fundamentals'],
    },
    {
      topic: 'Evaluation Metrics for LLMs',
      description: 'Master RAGAS, faithfulness, relevance, and context precision metrics. Learn how to build automated evaluation pipelines.',
      difficulty: 'intermediate',
      estimated_time_minutes: 45,
      tags: ['evaluation', 'metrics', 'RAGAS'],
      relevance_score: 0.87,
      prerequisites: ['RAG Architecture Patterns'],
    },
    {
      topic: 'Prompt Engineering Best Practices',
      description: 'Deep dive into few-shot learning, chain-of-thought prompting, and advanced prompt optimization techniques.',
      difficulty: 'beginner',
      estimated_time_minutes: 40,
      tags: ['prompting', 'LLM', 'optimization'],
      relevance_score: 0.85,
      prerequisites: [],
    },
    {
      topic: 'Knowledge Graph Integration',
      description: 'Combine vector search with knowledge graphs for enhanced retrieval. Learn about entity extraction and graph-based reasoning.',
      difficulty: 'advanced',
      estimated_time_minutes: 120,
      tags: ['knowledge graph', 'graph DB', 'reasoning'],
      relevance_score: 0.78,
      prerequisites: ['Multi-Agent Systems Design', 'RAG Architecture Patterns'],
    },
  ],
}

const difficultyConfig = {
  beginner: { label: 'Beginner', emoji: '🟢', color: 'text-green-400 bg-green-400/10 border-green-400/30' },
  intermediate: { label: 'Intermediate', emoji: '🟡', color: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30' },
  advanced: { label: 'Advanced', emoji: '🔴', color: 'text-red-400 bg-red-400/10 border-red-400/30' },
}

function TopicCard({ topic, index }: { topic: LearningTopic; index: number }) {
  const diff = difficultyConfig[topic.difficulty]
  const relevancePct = Math.round(topic.relevance_score * 100)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08 }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      className="rounded-2xl p-6 dark:bg-gray-900 bg-white border dark:border-gray-800 border-gray-200 hover:border-indigo-500/50 transition-all group cursor-pointer"
    >
      <div className="flex items-start justify-between mb-3">
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs border font-medium ${diff.color}`}>
          {diff.emoji} {diff.label}
        </span>
        <span className="text-sm font-semibold text-indigo-400">{relevancePct}% match</span>
      </div>

      <h3 className="text-base font-semibold dark:text-white text-gray-900 mb-2 group-hover:text-indigo-400 transition-colors">
        {topic.topic}
      </h3>
      <p className="text-sm dark:text-gray-400 text-gray-500 mb-4 leading-relaxed line-clamp-2">
        {topic.description}
      </p>

      {/* Relevance bar */}
      <div className="mb-4">
        <div className="h-1 dark:bg-gray-800 bg-gray-200 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${relevancePct}%` }}
            transition={{ duration: 0.8, delay: index * 0.08 + 0.3 }}
            className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full"
          />
        </div>
      </div>

      <div className="flex items-center gap-3 text-xs dark:text-gray-500 text-gray-400 mb-4">
        <span className="flex items-center gap-1">
          <Clock className="w-3.5 h-3.5" /> {topic.estimated_time_minutes} min
        </span>
        {topic.prerequisites.length > 0 && (
          <span className="flex items-center gap-1">
            <BookOpen className="w-3.5 h-3.5" /> {topic.prerequisites.length} prereq{topic.prerequisites.length > 1 ? 's' : ''}
          </span>
        )}
      </div>

      <div className="flex flex-wrap gap-1.5 mb-4">
        {topic.tags.map(tag => (
          <span key={tag} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs dark:bg-gray-800 bg-gray-100 dark:text-gray-400 text-gray-600">
            <Tag className="w-2.5 h-2.5" /> {tag}
          </span>
        ))}
      </div>

      <button className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600/0 hover:bg-indigo-600 border border-indigo-600/50 hover:border-indigo-600 text-indigo-400 hover:text-white text-sm font-medium transition-all">
        Start Learning <ChevronRight className="w-4 h-4" />
      </button>
    </motion.div>
  )
}

export default function RecommendationsPage() {
  const { addNotification, currentSessionId } = useStore()
  const [data, setData] = useState<RecommendationResponse>(MOCK_RECOMMENDATIONS)
  const [loading, setLoading] = useState(false)
  const [skillLevel, setSkillLevel] = useState<'beginner' | 'intermediate' | 'advanced'>('intermediate')
  const [currentTopic, setCurrentTopic] = useState('')
  const [filterDifficulty, setFilterDifficulty] = useState<string>('all')

  const loadRecommendations = async () => {
    setLoading(true)
    try {
      const result = await api.getRecommendations({
        skill_level: skillLevel,
        current_topic: currentTopic || undefined,
        session_id: currentSessionId ?? undefined,
      })
      setData(result)
    } catch {
      setData(MOCK_RECOMMENDATIONS)
    } finally {
      setLoading(false)
    }
  }

  const filtered = filterDifficulty === 'all'
    ? data.recommendations
    : data.recommendations.filter(t => t.difficulty === filterDifficulty)

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <h1 className="text-3xl font-bold dark:text-white text-gray-900 flex items-center gap-3">
          <Lightbulb className="w-8 h-8 text-yellow-500" /> Learning Recommendations
        </h1>
        <p className="dark:text-gray-400 text-gray-500 mt-1">Personalized topics based on your learning journey</p>
      </motion.div>

      {/* Milestone Banner */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0, transition: { delay: 0.1 } }}
        className="rounded-2xl p-5 mb-8 bg-gradient-to-r from-indigo-600/20 to-purple-600/20 border border-indigo-500/30">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm dark:text-gray-400 text-gray-500 mb-1">Next Milestone</p>
            <h3 className="text-lg font-bold dark:text-white text-gray-900">{data.next_milestone}</h3>
          </div>
          <div className="text-right">
            <p className="text-sm dark:text-gray-400 text-gray-500 mb-1">Current Level</p>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${difficultyConfig[data.current_level as keyof typeof difficultyConfig]?.color || 'text-indigo-400 bg-indigo-400/10'}`}>
              {difficultyConfig[data.current_level as keyof typeof difficultyConfig]?.emoji} {data.current_level}
            </span>
          </div>
        </div>
      </motion.div>

      {/* Controls */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1, transition: { delay: 0.15 } }}
        className="flex flex-wrap gap-4 mb-8 p-5 rounded-2xl dark:bg-gray-900 bg-white border dark:border-gray-800 border-gray-200">
        <div className="flex-1 min-w-48">
          <label className="block text-xs font-medium dark:text-gray-400 text-gray-500 mb-2">Your Skill Level</label>
          <div className="flex gap-2">
            {(['beginner', 'intermediate', 'advanced'] as const).map(level => (
              <button key={level} onClick={() => setSkillLevel(level)}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all capitalize ${
                  skillLevel === level ? 'bg-indigo-600 text-white' : 'dark:bg-gray-800 bg-gray-100 dark:text-gray-400 text-gray-600 dark:hover:bg-gray-700 hover:bg-gray-200'
                }`}>
                {level}
              </button>
            ))}
          </div>
        </div>
        <div className="flex-1 min-w-48">
          <label className="block text-xs font-medium dark:text-gray-400 text-gray-500 mb-2">Current Topic (optional)</label>
          <input value={currentTopic} onChange={e => setCurrentTopic(e.target.value)}
            placeholder="e.g. RAG, embeddings..."
            className="w-full px-3 py-1.5 rounded-xl dark:bg-gray-800 bg-gray-100 dark:text-white text-gray-900 dark:placeholder-gray-600 placeholder-gray-400 border dark:border-gray-700 border-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm" />
        </div>
        <div className="flex items-end">
          <button onClick={loadRecommendations} disabled={loading}
            className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-xl text-sm font-medium transition-colors flex items-center gap-2">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
      </motion.div>

      {/* Difficulty filter */}
      <div className="flex gap-2 mb-6">
        {['all', 'beginner', 'intermediate', 'advanced'].map(f => (
          <button key={f} onClick={() => setFilterDifficulty(f)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all capitalize ${
              filterDifficulty === f ? 'bg-indigo-600 text-white' : 'dark:bg-gray-800 bg-gray-100 dark:text-gray-400 text-gray-600 dark:hover:bg-gray-700 hover:bg-gray-200'
            }`}>
            {f === 'all' ? 'All Topics' : `${difficultyConfig[f as keyof typeof difficultyConfig].emoji} ${f}`}
          </button>
        ))}
        <span className="ml-auto text-sm dark:text-gray-500 text-gray-400 self-center">
          {filtered.length} topic{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Topic Cards */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1,2,3,4,5,6].map(i => (
            <div key={i} className="h-80 dark:bg-gray-800 bg-gray-200 rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 dark:text-gray-500 text-gray-400">
          <Lightbulb className="w-16 h-16 mx-auto mb-4 opacity-20" />
          <p className="text-lg">No topics found for this filter</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map((topic, i) => (
            <TopicCard key={topic.topic} topic={topic} index={i} />
          ))}
        </div>
      )}
    </div>
  )
}
