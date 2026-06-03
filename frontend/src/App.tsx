import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import NeuralBackground from './components/NeuralBackground'

const agents = [
  { name: 'CEO Agent', role: 'Strategic Orchestrator', color: '#6366f1', icon: '👔', tasks: 48, confidence: 97 },
  { name: 'Research Agent', role: 'Market Intelligence', color: '#06b6d4', icon: '🔬', tasks: 124, confidence: 94 },
  { name: 'Sales Agent', role: 'Revenue Engine', color: '#10b981', icon: '💼', tasks: 87, confidence: 91 },
  { name: 'Marketing Agent', role: 'Growth Strategy', color: '#f59e0b', icon: '📣', tasks: 63, confidence: 89 },
  { name: 'Finance Agent', role: 'Financial Intelligence', color: '#ec4899', icon: '💰', tasks: 52, confidence: 95 },
  { name: 'Ops Agent', role: 'Operations Control', color: '#8b5cf6', icon: '⚙️', tasks: 71, confidence: 92 },
  { name: 'Web Agent', role: 'Web Intelligence', color: '#14b8a6', icon: '🌐', tasks: 98, confidence: 88 },
  { name: 'Memory Agent', role: 'Context Memory', color: '#f97316', icon: '🧠', tasks: 156, confidence: 96 },
]

const chartData = [
  { name: 'Mon', tasks: 12 },
  { name: 'Tue', tasks: 19 },
  { name: 'Wed', tasks: 15 },
  { name: 'Thu', tasks: 28 },
  { name: 'Fri', tasks: 24 },
  { name: 'Sat', tasks: 31 },
  { name: 'Sun', tasks: 22 },
]

const activityFeed = [
  { agent: 'Research Agent', action: 'Discovered 50 AI startups in Europe', time: '2m ago', color: '#06b6d4' },
  { agent: 'Sales Agent', action: 'Generated outreach campaign for 20 prospects', time: '5m ago', color: '#10b981' },
  { agent: 'Marketing Agent', action: 'Created social media strategy', time: '8m ago', color: '#f59e0b' },
  { agent: 'Finance Agent', action: 'Estimated budget: €250,000', time: '12m ago', color: '#ec4899' },
  { agent: 'CEO Agent', action: 'Compiled executive summary report', time: '15m ago', color: '#6366f1' },
]

function CountUp({ target }: { target: number }) {
  const [count, setCount] = useState(0)
  useEffect(() => {
    const step = target / 50
    const timer = setInterval(() => {
      setCount(prev => {
        if (prev >= target) { clearInterval(timer); return target }
        return Math.min(prev + step, target)
      })
    }, 30)
    return () => clearInterval(timer)
  }, [target])
  return <>{Math.floor(count)}</>
}

function parseResult(result: string) {
  return result.split('---').map(s => s.trim()).filter(Boolean)
}

function getSectionColor(section: string) {
  const s = section.toUpperCase()
  if (s.includes('CEO')) return '#6366f1'
  if (s.includes('RESEARCH')) return '#06b6d4'
  if (s.includes('WEB')) return '#14b8a6'
  if (s.includes('SALES')) return '#10b981'
  if (s.includes('MARKETING')) return '#f59e0b'
  if (s.includes('FINANCE')) return '#ec4899'
  if (s.includes('OPERATIONS')) return '#8b5cf6'
  if (s.includes('MEMORY')) return '#f97316'
  return '#6366f1'
}

export default function App() {
  const [task, setTask] = useState('')
  const [sections, setSections] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [activeAgents, setActiveAgents] = useState<string[]>([])
  const [currentAgent, setCurrentAgent] = useState('')
  const [view, setView] = useState<'dashboard' | 'tasks'>('dashboard')
  const [showPalette, setShowPalette] = useState(false)

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'k') {
        e.preventDefault()
        setShowPalette(prev => !prev)
      }
      if (e.key === 'Escape') setShowPalette(false)
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [])

  const runTask = async () => {
    if (!task) return
    setLoading(true)
    setSections([])
    setView('tasks')

    for (const agent of agents) {
      setCurrentAgent(agent.name)
      setActiveAgents(prev => [...prev, agent.name])
      await new Promise(r => setTimeout(r, 300))
    }

    try {
      const res = await fetch('http://127.0.0.1:8000/tasks/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: task, description: task })
      })
      const data = await res.json()
      if (data.result) setSections(parseResult(data.result))
    } catch (e) {
      setSections(['❌ Error connecting to backend'])
    }

    setActiveAgents([])
    setCurrentAgent('')
    setLoading(false)
  }

  return (
    <div className="min-h-screen text-white" style={{ background: '#050816' }}>
      <NeuralBackground />

      {/* Navbar */}
      <div className="border-b border-white/5 px-8 py-4 flex items-center justify-between sticky top-0 z-50"
        style={{ background: 'rgba(5,8,22,0.9)', backdropFilter: 'blur(20px)' }}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold"
            style={{ background: 'linear-gradient(135deg, #6366f1, #00E5FF)' }}>⚡</div>
          <div>
            <span className="font-bold text-lg"
              style={{ background: 'linear-gradient(90deg, #6366f1, #00E5FF)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              Enterprise AI OS
            </span>
            <span className="text-xs text-gray-600 ml-2">v1.0</span>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <button onClick={() => setView('dashboard')}
            className={`text-sm transition-colors ${view === 'dashboard' ? 'text-white' : 'text-gray-600 hover:text-gray-400'}`}>
            Dashboard
          </button>
          <button onClick={() => setView('tasks')}
            className={`text-sm transition-colors ${view === 'tasks' ? 'text-white' : 'text-gray-600 hover:text-gray-400'}`}>
            Tasks
          </button>
          <button onClick={() => setShowPalette(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-white/10 text-xs text-gray-500 hover:text-gray-300 transition-all">
            <span>⌘</span> Ctrl+K
          </button>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-green-500/20"
            style={{ background: 'rgba(16,185,129,0.1)' }}>
            <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
            <span className="text-xs text-green-400">8 Agents Online</span>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6 relative z-10">
        <AnimatePresence mode="wait">
          {view === 'dashboard' ? (
            <motion.div key="dashboard" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>

              {/* Hero */}
              <div className="text-center py-16">
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-indigo-500/30 text-xs text-indigo-400 mb-6"
                  style={{ background: 'rgba(99,102,241,0.1)' }}>
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse inline-block" />
                  Autonomous Multi-Agent Operating System
                </motion.div>
                <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
                  className="text-6xl font-bold mb-4 leading-tight">
                  <span style={{ background: 'linear-gradient(135deg, #ffffff 0%, #94a3b8 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                    Enterprise AI OS
                  </span>
                </motion.h1>
                <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
                  className="text-gray-500 text-lg mb-8 max-w-xl mx-auto">
                  8 specialized AI agents collaborating autonomously to complete your business tasks
                </motion.p>
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
                  className="flex gap-3 justify-center">
                  <button onClick={() => setView('tasks')}
                    className="px-6 py-3 rounded-xl text-sm font-semibold transition-all hover:scale-105"
                    style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}>
                    ▶ Launch Task
                  </button>
                  <button className="px-6 py-3 rounded-xl text-sm font-semibold border border-white/10 text-gray-400 hover:text-white transition-all">
                    View Demo
                  </button>
                </motion.div>
              </div>

              {/* KPI Cards */}
              <div className="grid grid-cols-4 gap-4 mb-8">
                {[
                  { label: 'Active Agents', value: 8, suffix: '', color: '#6366f1', icon: '🤖' },
                  { label: 'Tasks Today', value: 124, suffix: '', color: '#10b981', icon: '✅' },
                  { label: 'Avg Confidence', value: 93, suffix: '%', color: '#06b6d4', icon: '🎯' },
                  { label: 'Opportunities', value: 2, suffix: 'M+', color: '#f59e0b', icon: '💡' },
                ].map((kpi, i) => (
                  <motion.div key={i} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}
                    className="rounded-2xl p-5 border border-white/5 hover:border-white/10 transition-all"
                    style={{ background: 'rgba(15,23,42,0.65)', backdropFilter: 'blur(20px)' }}>
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-2xl">{kpi.icon}</span>
                      <div className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: kpi.color, boxShadow: `0 0 8px ${kpi.color}` }} />
                    </div>
                    <div className="text-3xl font-bold mb-1" style={{ color: kpi.color }}>
                      <CountUp target={kpi.value} />{kpi.suffix}
                    </div>
                    <div className="text-xs text-gray-500">{kpi.label}</div>
                  </motion.div>
                ))}
              </div>

              {/* Agent Grid */}
              <div className="mb-8">
                <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-widest mb-4">Agent Network</h2>
                <div className="grid grid-cols-4 gap-4">
                  {agents.map((agent, i) => (
                    <motion.div key={i} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: i * 0.05 }} whileHover={{ scale: 1.02 }}
                      className="rounded-2xl p-4 border border-white/5 cursor-pointer transition-all"
                      style={{ background: 'rgba(15,23,42,0.65)', backdropFilter: 'blur(20px)' }}>
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-2xl">{agent.icon}</span>
                        <div className="flex items-center gap-1">
                          <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                          <span className="text-xs text-green-400">Active</span>
                        </div>
                      </div>
                      <p className="font-semibold text-sm mb-1">{agent.name}</p>
                      <p className="text-xs text-gray-600 mb-3">{agent.role}</p>
                      <div className="flex justify-between text-xs mb-2">
                        <div>
                          <div className="text-gray-600">Tasks</div>
                          <div className="font-bold" style={{ color: agent.color }}>{agent.tasks}</div>
                        </div>
                        <div>
                          <div className="text-gray-600">Confidence</div>
                          <div className="font-bold" style={{ color: agent.color }}>{agent.confidence}%</div>
                        </div>
                      </div>
                      <div className="h-1 rounded-full bg-white/5">
                        <motion.div initial={{ width: 0 }} animate={{ width: `${agent.confidence}%` }}
                          transition={{ delay: i * 0.1, duration: 1 }}
                          className="h-full rounded-full" style={{ backgroundColor: agent.color }} />
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>

              {/* Charts + Activity */}
              <div className="grid grid-cols-3 gap-6">
                <div className="col-span-2 rounded-2xl p-5 border border-white/5" style={{ background: 'rgba(15,23,42,0.65)' }}>
                  <h3 className="text-sm font-semibold text-gray-400 mb-4">Task Execution This Week</h3>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={chartData}>
                      <XAxis dataKey="name" tick={{ fill: '#475569', fontSize: 11 }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fill: '#475569', fontSize: 11 }} axisLine={false} tickLine={false} />
                      <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 8, fontSize: 12 }} />
                      <Bar dataKey="tasks" fill="#6366f1" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="rounded-2xl p-5 border border-white/5" style={{ background: 'rgba(15,23,42,0.65)' }}>
                  <h3 className="text-sm font-semibold text-gray-400 mb-4">Live Activity</h3>
                  <div className="space-y-3">
                    {activityFeed.map((item, i) => (
                      <motion.div key={i} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.1 }} className="flex gap-3 items-start">
                        <div className="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0" style={{ backgroundColor: item.color }} />
                        <div>
                          <p className="text-xs font-semibold" style={{ color: item.color }}>{item.agent}</p>
                          <p className="text-xs text-gray-600">{item.action}</p>
                          <p className="text-xs text-gray-700">{item.time}</p>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>

          ) : (
            <motion.div key="tasks" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>

              {/* Task Input */}
              <div className="rounded-2xl p-6 border border-white/5 mb-6" style={{ background: 'rgba(15,23,42,0.65)' }}>
                <p className="text-xs text-indigo-400 uppercase tracking-widest mb-3 font-semibold">Delegate to CEO Agent</p>
                <div className="flex gap-3">
                  <input
                    className="flex-1 rounded-xl px-4 py-3 text-white outline-none text-sm placeholder-gray-700 border border-white/5 focus:border-indigo-500 transition-colors"
                    style={{ background: '#050816' }}
                    placeholder="e.g. Research AI startups in Europe and create outreach strategy..."
                    value={task}
                    onChange={e => setTask(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && !loading && runTask()}
                  />
                  <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                    onClick={runTask} disabled={loading}
                    className="px-6 py-3 rounded-xl font-semibold text-sm disabled:opacity-50 whitespace-nowrap"
                    style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}>
                    {loading ? '⚡ Working...' : '▶ Run Task'}
                  </motion.button>
                </div>
              </div>

              {/* Agent Status */}
              <div className="grid grid-cols-4 gap-3 mb-6">
                {agents.map((agent, i) => (
                  <motion.div key={i}
                    animate={{ borderColor: activeAgents.includes(agent.name) ? agent.color : 'rgba(255,255,255,0.05)' }}
                    className="rounded-xl p-3 border transition-all"
                    style={{ background: 'rgba(15,23,42,0.65)' }}>
                    <div className="flex items-center gap-2">
                      <span>{agent.icon}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold truncate">{agent.name}</p>
                      </div>
                      <motion.div className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ backgroundColor: agent.color }}
                        animate={{ scale: activeAgents.includes(agent.name) ? [1, 1.5, 1] : 1, opacity: activeAgents.includes(agent.name) ? 1 : 0.3 }}
                        transition={{ repeat: activeAgents.includes(agent.name) ? Infinity : 0, duration: 0.8 }} />
                    </div>
                    {currentAgent === agent.name && (
                      <motion.div initial={{ width: 0 }} animate={{ width: '100%' }}
                        className="h-0.5 rounded-full mt-2" style={{ backgroundColor: agent.color }} />
                    )}
                  </motion.div>
                ))}
              </div>

              {/* Loading */}
              <AnimatePresence>
                {loading && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    className="rounded-2xl p-8 border border-white/5 mb-6 text-center"
                    style={{ background: 'rgba(15,23,42,0.65)' }}>
                    <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1.5, ease: 'linear' }}
                      className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full mx-auto mb-4" />
                    <p className="text-gray-400 text-sm">{currentAgent ? `${currentAgent} is working...` : 'Initializing agents...'}</p>
                    <p className="text-gray-700 text-xs mt-1">All agents collaborating on your task</p>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Results */}
              {sections.length > 0 && (
                <div className="space-y-4">
                  {sections.map((section, i) => {
                    const color = getSectionColor(section)
                    return (
                      <motion.div key={i} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.08 }}
                        className="rounded-2xl p-6 border border-white/5"
                        style={{ background: 'rgba(15,23,42,0.65)', borderLeftColor: color, borderLeftWidth: 3 }}>
                        <div className="text-sm text-gray-300 leading-relaxed prose prose-invert prose-sm max-w-none">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{section}</ReactMarkdown>
                        </div>
                      </motion.div>
                    )
                  })}
                </div>
              )}

              {!loading && sections.length === 0 && (
                <div className="text-center py-20">
                  <div className="text-6xl mb-4">⚡</div>
                  <h2 className="text-xl font-semibold text-gray-500 mb-2">Ready to Execute</h2>
                  <p className="text-gray-700 text-sm">Type a business task and all 8 agents will collaborate</p>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Command Palette */}
      <AnimatePresence>
        {showPalette && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-start justify-center pt-32"
            style={{ background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(8px)' }}
            onClick={() => setShowPalette(false)}>
            <motion.div initial={{ opacity: 0, scale: 0.95, y: -20 }} animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -20 }}
              className="w-full max-w-lg rounded-2xl border border-white/10 overflow-hidden"
              style={{ background: 'rgba(15,23,42,0.95)' }}
              onClick={e => e.stopPropagation()}>
              <div className="flex items-center gap-3 px-4 py-3 border-b border-white/5">
                <span className="text-gray-500">⌘</span>
                <input autoFocus
                  className="flex-1 bg-transparent text-white outline-none text-sm placeholder-gray-600"
                  placeholder="Search agents, tasks, commands..." />
                <span className="text-xs text-gray-600 px-2 py-1 rounded border border-white/10">ESC</span>
              </div>
              <div className="p-2">
                {[
                  { icon: '▶', label: 'Run New Task', action: () => { setView('tasks'); setShowPalette(false) } },
                  { icon: '📊', label: 'Go to Dashboard', action: () => { setView('dashboard'); setShowPalette(false) } },
                  { icon: '🤖', label: 'View All Agents', action: () => { setView('dashboard'); setShowPalette(false) } },
                  { icon: '📋', label: 'View Task History', action: () => { setView('tasks'); setShowPalette(false) } },
                ].map((cmd, i) => (
                  <button key={i} onClick={cmd.action}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-gray-300 hover:text-white hover:bg-white/5 transition-all text-left">
                    <span>{cmd.icon}</span>
                    {cmd.label}
                  </button>
                ))}
              </div>
              <div className="px-4 py-2 border-t border-white/5">
                <span className="text-xs text-gray-700">Press Ctrl+K to toggle • ESC to close</span>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}