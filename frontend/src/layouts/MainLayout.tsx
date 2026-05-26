import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard, MessageSquare, Upload, BarChart3,
  Lightbulb, History, Brain, Sun, Moon, X,
  CheckCircle, AlertCircle, Info, AlertTriangle, Wifi,
} from 'lucide-react'
import { useStore } from '../store/useStore'

const navItems = [
  { to: '/',               label: 'Dashboard',       icon: LayoutDashboard, exact: true },
  { to: '/chat',           label: 'Chat',             icon: MessageSquare },
  { to: '/upload',         label: 'Upload PDFs',      icon: Upload },
  { to: '/analytics',      label: 'Analytics',        icon: BarChart3 },
  { to: '/recommendations',label: 'Recommendations',  icon: Lightbulb },
  { to: '/history',        label: 'History',          icon: History },
]

const notifIcons = {
  success: CheckCircle,
  error:   AlertCircle,
  info:    Info,
  warning: AlertTriangle,
}

const notifStyles = {
  success: 'border-teal-400 bg-teal-50   text-teal-800',
  error:   'border-red-400   bg-red-50   text-red-800',
  info:    'border-teal-300  bg-teal-50  text-teal-700',
  warning: 'border-gold-400  bg-amber-50 text-amber-800',
}

export default function MainLayout() {
  const { theme, toggleTheme, notifications, removeNotification } = useStore()
  const location = useLocation()
  const isDark = theme === 'dark'

  return (
    <div className={`flex h-screen overflow-hidden font-sans ${
      isDark
        ? 'bg-teal-800 text-cream-100'
        : 'bg-cream-100 text-teal-900'
    }`}>

      {/* ── Sidebar ── */}
      <aside className={`w-64 flex-shrink-0 flex flex-col z-20 ${
        isDark
          ? 'bg-teal-900 border-r border-teal-800'
          : 'bg-teal-700 border-r border-teal-600'
      }`}>

        {/* Logo */}
        <div className="p-6 border-b border-teal-600/40">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-2xl bg-white/15 backdrop-blur-sm flex items-center justify-center shadow-teal border border-white/20">
              <Brain className="w-6 h-6 text-cream-100" />
            </div>
            <div>
              <h1 className="font-bold text-sm text-cream-50 tracking-wide">AI Learning</h1>
              <p className="text-xs text-teal-200 mt-0.5">Smart Assistant v1.0</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          <p className="text-[10px] font-semibold text-teal-300 uppercase tracking-widest px-3 mb-3">
            Navigation
          </p>
          {navItems.map(({ to, label, icon: Icon, exact }) => (
            <NavLink
              key={to}
              to={to}
              end={exact}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group ${
                  isActive
                    ? 'nav-active text-white'
                    : 'text-teal-100 hover:bg-teal-600/50 hover:text-white'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon className={`w-[18px] h-[18px] transition-transform group-hover:scale-110 flex-shrink-0 ${
                    isActive ? 'text-white' : 'text-teal-200'
                  }`} />
                  <span className="flex-1">{label}</span>
                  {isActive && (
                    <motion.div
                      layoutId="activeNav"
                      className="w-1.5 h-1.5 rounded-full bg-cream-200/80"
                    />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-teal-600/40 space-y-3">
          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-teal-100 hover:bg-teal-600/50 hover:text-white transition-all"
          >
            {isDark
              ? <><Sun  className="w-4 h-4 text-gold-300" /> <span>Light Mode</span></>
              : <><Moon className="w-4 h-4 text-teal-200" /> <span>Dark Mode</span></>
            }
          </button>

          {/* Status */}
          <div className="flex items-center gap-2 px-3">
            <Wifi className="w-3.5 h-3.5 text-teal-300" />
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse-slow" />
            <span className="text-xs text-teal-300">Backend ready</span>
          </div>
        </div>
      </aside>

      {/* ── Main content ── */}
      <main className={`flex-1 overflow-y-auto ${
        isDark ? 'bg-teal-800' : 'bg-cream-100'
      }`}>
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y:  0 }}
            exit={  { opacity: 0, y: -10 }}
            transition={{ duration: 0.22 }}
            className="h-full"
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>

      {/* ── Notifications ── */}
      <div className="fixed bottom-4 right-4 z-50 space-y-2 max-w-sm">
        <AnimatePresence>
          {notifications.map((notif) => {
            const Icon = notifIcons[notif.type]
            return (
              <motion.div
                key={notif.id}
                initial={{ opacity: 0, x: 60 }}
                animate={{ opacity: 1, x: 0  }}
                exit={  { opacity: 0, x: 60  }}
                className={`flex items-start gap-3 p-4 rounded-2xl border shadow-cream backdrop-blur-sm ${notifStyles[notif.type]}`}
              >
                <Icon className="w-5 h-5 mt-0.5 flex-shrink-0" />
                <p className="text-sm flex-1">{notif.message}</p>
                <button onClick={() => removeNotification(notif.id)} className="opacity-50 hover:opacity-100 transition-opacity">
                  <X className="w-4 h-4" />
                </button>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </div>
  )
}
