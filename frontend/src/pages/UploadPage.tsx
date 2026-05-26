import { useState, useRef, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, File, Trash2, CheckCircle, AlertCircle, X, RefreshCw, FolderOpen } from 'lucide-react'
import api from '../services/api'
import { DocumentListItem } from '../types'
import { useStore } from '../store/useStore'

interface UploadItem {
  id: string
  file: File
  status: 'pending' | 'uploading' | 'success' | 'error'
  progress: number
  error?: string
  result?: DocumentListItem
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export default function UploadPage() {
  const { addNotification } = useStore()
  const [isDragging, setIsDragging] = useState(false)
  const [uploads, setUploads] = useState<UploadItem[]>([])
  const [documents, setDocuments] = useState<DocumentListItem[]>([])
  const [docsLoading, setDocsLoading] = useState(true)
  const [collection, setCollection] = useState('default')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const loadDocuments = useCallback(async () => {
    setDocsLoading(true)
    try {
      const docs = await api.listDocuments()
      setDocuments(docs)
    } catch {
      setDocuments([])
    } finally {
      setDocsLoading(false)
    }
  }, [])

  useEffect(() => { loadDocuments() }, [loadDocuments])

  const validateFile = (file: File): string | null => {
    if (!['application/pdf', 'text/plain', 'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'].includes(file.type)
      && !file.name.match(/\.(pdf|txt|doc|docx)$/i)) {
      return 'Only PDF, TXT, DOC, DOCX files allowed'
    }
    if (file.size > 50 * 1024 * 1024) return 'File must be under 50MB'
    return null
  }

  const addFiles = (files: FileList | null) => {
    if (!files) return
    const newUploads: UploadItem[] = []
    Array.from(files).forEach(file => {
      const error = validateFile(file)
      newUploads.push({
        id: Date.now().toString() + Math.random(),
        file,
        status: error ? 'error' : 'pending',
        progress: 0,
        error: error ?? undefined,
      })
    })
    setUploads(prev => [...prev, ...newUploads])
  }

  const uploadFile = async (item: UploadItem) => {
    setUploads(prev => prev.map(u => u.id === item.id ? { ...u, status: 'uploading', progress: 10 } : u))
    // Simulate progress
    const progressInterval = setInterval(() => {
      setUploads(prev => prev.map(u => u.id === item.id && u.progress < 85
        ? { ...u, progress: u.progress + 15 } : u))
    }, 300)
    try {
      const result = await api.uploadDocument(item.file, collection)
      clearInterval(progressInterval)
      setUploads(prev => prev.map(u => u.id === item.id ? { ...u, status: 'success', progress: 100 } : u))
      addNotification('success', `${item.file.name} uploaded successfully (${result.chunks_created} chunks)`)
      loadDocuments()
    } catch (err: any) {
      clearInterval(progressInterval)
      setUploads(prev => prev.map(u => u.id === item.id ? { ...u, status: 'error', error: err.message } : u))
      addNotification('error', `Failed to upload ${item.file.name}`)
    }
  }

  const uploadAll = () => {
    uploads.filter(u => u.status === 'pending').forEach(uploadFile)
  }

  const removeUpload = (id: string) => {
    setUploads(prev => prev.filter(u => u.id !== id))
  }

  const deleteDocument = async (docId: string, filename: string) => {
    try {
      await api.deleteDocument(docId)
      setDocuments(prev => prev.filter(d => d.document_id !== docId))
      addNotification('success', `${filename} deleted`)
    } catch (err: any) {
      addNotification('error', err.message)
    }
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    addFiles(e.dataTransfer.files)
  }, [])

  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(true) }
  const handleDragLeave = () => setIsDragging(false)

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <h1 className="text-3xl font-bold dark:text-white text-gray-900">Upload Documents</h1>
        <p className="dark:text-gray-400 text-gray-500 mt-1">Upload PDFs and documents to build your knowledge base</p>
      </motion.div>

      {/* Collection name input */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1, transition: { delay: 0.1 } }}
        className="mb-6 flex items-center gap-4">
        <label className="text-sm font-medium dark:text-gray-300 text-gray-700 flex items-center gap-2">
          <FolderOpen className="w-4 h-4 text-indigo-500" /> Collection:
        </label>
        <input value={collection} onChange={e => setCollection(e.target.value)}
          className="px-4 py-2 rounded-xl dark:bg-gray-800 bg-gray-100 dark:text-white text-gray-900 border dark:border-gray-700 border-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm w-48"
          placeholder="default" />
      </motion.div>

      {/* Drop Zone */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0, transition: { delay: 0.15 } }}
        onDrop={handleDrop} onDragOver={handleDragOver} onDragLeave={handleDragLeave}
        onClick={() => fileInputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all mb-6 ${
          isDragging
            ? 'border-indigo-500 bg-indigo-500/10 scale-[1.01]'
            : 'dark:border-gray-700 border-gray-300 dark:hover:border-indigo-600 hover:border-indigo-400 dark:bg-gray-900 bg-white'
        }`}>
        <input ref={fileInputRef} type="file" multiple accept=".pdf,.txt,.doc,.docx" className="hidden"
          onChange={e => addFiles(e.target.files)} />
        <motion.div animate={isDragging ? { scale: 1.1 } : { scale: 1 }}
          className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-indigo-600/20 flex items-center justify-center">
          <Upload className={`w-8 h-8 ${isDragging ? 'text-indigo-400' : 'text-indigo-500'}`} />
        </motion.div>
        <h3 className="text-lg font-semibold dark:text-white text-gray-900 mb-2">
          {isDragging ? 'Drop files here!' : 'Drag & drop files here'}
        </h3>
        <p className="dark:text-gray-400 text-gray-500 text-sm mb-4">or click to browse</p>
        <p className="text-xs dark:text-gray-600 text-gray-400">Supports PDF, TXT, DOC, DOCX — up to 50MB each</p>
      </motion.div>

      {/* Upload Queue */}
      <AnimatePresence>
        {uploads.length > 0 && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }} className="mb-8">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold dark:text-white text-gray-900">Upload Queue ({uploads.length})</h2>
              {uploads.some(u => u.status === 'pending') && (
                <button onClick={uploadAll}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-medium transition-colors flex items-center gap-2">
                  <Upload className="w-4 h-4" /> Upload All
                </button>
              )}
            </div>
            <div className="space-y-3">
              {uploads.map(item => (
                <motion.div key={item.id} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  className="flex items-center gap-4 p-4 rounded-xl dark:bg-gray-900 bg-white border dark:border-gray-800 border-gray-200">
                  <div className="w-10 h-10 rounded-xl bg-indigo-600/20 flex items-center justify-center flex-shrink-0">
                    <File className="w-5 h-5 text-indigo-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium dark:text-white text-gray-900 truncate">{item.file.name}</p>
                    <p className="text-xs dark:text-gray-500 text-gray-400">{formatBytes(item.file.size)}</p>
                    {item.status === 'uploading' && (
                      <div className="mt-2 h-1.5 dark:bg-gray-700 bg-gray-200 rounded-full overflow-hidden">
                        <motion.div animate={{ width: `${item.progress}%` }}
                          className="h-full bg-indigo-500 rounded-full" transition={{ duration: 0.3 }} />
                      </div>
                    )}
                    {item.error && <p className="text-xs text-red-400 mt-1">{item.error}</p>}
                  </div>
                  <div className="flex items-center gap-2">
                    {item.status === 'success' && <CheckCircle className="w-5 h-5 text-green-500" />}
                    {item.status === 'error' && <AlertCircle className="w-5 h-5 text-red-500" />}
                    {item.status === 'pending' && (
                      <button onClick={() => uploadFile(item)}
                        className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs transition-colors">
                        Upload
                      </button>
                    )}
                    <button onClick={() => removeUpload(item.id)}
                      className="p-1.5 dark:hover:bg-gray-800 hover:bg-gray-100 rounded-lg transition-colors">
                      <X className="w-4 h-4 dark:text-gray-500 text-gray-400" />
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Documents List */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0, transition: { delay: 0.25 } }}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold dark:text-white text-gray-900">Indexed Documents</h2>
          <button onClick={loadDocuments} className="p-2 dark:hover:bg-gray-800 hover:bg-gray-100 rounded-xl transition-colors">
            <RefreshCw className={`w-4 h-4 dark:text-gray-400 text-gray-600 ${docsLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
        {docsLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-16 dark:bg-gray-800 bg-gray-200 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-12 dark:text-gray-500 text-gray-400">
            <File className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>No documents indexed yet. Upload some files above.</p>
          </div>
        ) : (
          <div className="rounded-2xl dark:bg-gray-900 bg-white border dark:border-gray-800 border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="dark:border-b dark:border-gray-800 border-b border-gray-200">
                  <th className="text-left px-6 py-4 dark:text-gray-400 text-gray-500 font-medium">Filename</th>
                  <th className="text-left px-6 py-4 dark:text-gray-400 text-gray-500 font-medium hidden md:table-cell">Collection</th>
                  <th className="text-left px-6 py-4 dark:text-gray-400 text-gray-500 font-medium hidden lg:table-cell">Chunks</th>
                  <th className="text-left px-6 py-4 dark:text-gray-400 text-gray-500 font-medium hidden lg:table-cell">Uploaded</th>
                  <th className="text-left px-6 py-4 dark:text-gray-400 text-gray-500 font-medium">Status</th>
                  <th className="px-6 py-4" />
                </tr>
              </thead>
              <tbody>
                {documents.map((doc, i) => (
                  <motion.tr key={doc.document_id} initial={{ opacity: 0 }} animate={{ opacity: 1, transition: { delay: i * 0.05 } }}
                    className="border-t dark:border-gray-800 border-gray-100 dark:hover:bg-gray-800/50 hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-indigo-600/20 flex items-center justify-center flex-shrink-0">
                          <File className="w-4 h-4 text-indigo-500" />
                        </div>
                        <span className="font-medium dark:text-white text-gray-900 truncate max-w-xs">{doc.filename}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 dark:text-gray-400 text-gray-500 hidden md:table-cell">{doc.collection_name}</td>
                    <td className="px-6 py-4 dark:text-gray-400 text-gray-500 hidden lg:table-cell">{doc.chunk_count}</td>
                    <td className="px-6 py-4 dark:text-gray-400 text-gray-500 hidden lg:table-cell">{formatDate(doc.upload_date)}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${
                        doc.status === 'indexed' ? 'bg-green-500/10 text-green-400' : 'bg-yellow-500/10 text-yellow-400'
                      }`}>
                        <div className="w-1.5 h-1.5 rounded-full bg-current" />
                        {doc.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <button onClick={() => deleteDocument(doc.document_id, doc.filename)}
                        className="p-2 text-red-400 hover:text-red-300 dark:hover:bg-red-400/10 hover:bg-red-50 rounded-lg transition-all">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </motion.div>
    </div>
  )
}
