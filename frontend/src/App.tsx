import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import NeuralBackground from './components/NeuralBackground'

type AgentStatus = 'idle' | 'thinking' | 'executing' | 'completed' | 'waiting'

const agentStatusColors: Record<AgentStatus, string> = {
  idle: '#4b5563',
  thinking: '#06b6d4',
  executing: '#f59e0b',
  waiting: '#8b5cf6',
  completed: '#10b981',
}

const agentStatusLabels: Record<AgentStatus, string> = {
  idle: 'Idle',
  thinking: 'Thinking',
  executing: 'Executing',
  waiting: 'Waiting',
  completed: 'Completed',
}

const initialAgents = [
  { id: 'ceo', name: 'CEO Agent', role: 'Orchestrator', color: '#6366f1', icon: '👔', x: 400, y: 200, tasks: 48, memory: 87, messages: 234, success: 97, status: 'idle' as AgentStatus },
  { id: 'research', name: 'Research', role: 'Intelligence', color: '#06b6d4', icon: '🔬', x: 200, y: 100, tasks: 124, memory: 72, messages: 456, success: 94, status: 'idle' as AgentStatus },
  { id: 'sales', name: 'Sales', role: 'Revenue', color: '#10b981', icon: '💼', x: 620, y: 100, tasks: 87, memory: 65, messages: 321, success: 91, status: 'idle' as AgentStatus },
  { id: 'marketing', name: 'Marketing', role: 'Growth', color: '#f59e0b', icon: '📣', x: 150, y: 320, tasks: 63, memory: 58, messages: 198, success: 89, status: 'idle' as AgentStatus },
  { id: 'finance', name: 'Finance', role: 'Financial', color: '#ec4899', icon: '💰', x: 660, y: 320, tasks: 52, memory: 81, messages: 167, success: 95, status: 'idle' as AgentStatus },
  { id: 'ops', name: 'Operations', role: 'Control', color: '#8b5cf6', icon: '⚙️', x: 220, y: 420, tasks: 71, memory: 69, messages: 289, success: 92, status: 'idle' as AgentStatus },
  { id: 'web', name: 'Web Intel', role: 'Research', color: '#14b8a6', icon: '🌐', x: 600, y: 420, tasks: 98, memory: 74, messages: 412, success: 88, status: 'idle' as AgentStatus },
  { id: 'memory', name: 'Memory', role: 'Storage', color: '#f97316', icon: '🧠', x: 400, y: 370, tasks: 156, memory: 92, messages: 567, success: 96, status: 'idle' as AgentStatus },
]

const connections = [
  { from: 'ceo', to: 'research' },
  { from: 'ceo', to: 'sales' },
  { from: 'ceo', to: 'marketing' },
  { from: 'ceo', to: 'finance' },
  { from: 'ceo', to: 'ops' },
  { from: 'ceo', to: 'memory' },
  { from: 'research', to: 'memory' },
  { from: 'sales', to: 'memory' },
  { from: 'marketing', to: 'memory' },
  { from: 'web', to: 'research' },
  { from: 'ops', to: 'memory' },
]

const workflowSteps = [
  { label: 'CEO', color: '#6366f1', icon: '👔' },
  { label: 'Research', color: '#06b6d4', icon: '🔬' },
  { label: 'Memory', color: '#f97316', icon: '🧠' },
  { label: 'Sales', color: '#10b981', icon: '💼' },
  { label: 'Marketing', color: '#f59e0b', icon: '📣' },
  { label: 'Report', color: '#8b5cf6', icon: '📊' },
]

const eventTemplates = [
  { agent: 'Research', action: 'Scanning European AI market...', color: '#06b6d4' },
  { agent: 'Research', action: '50 startups identified', color: '#06b6d4' },
  { agent: 'CEO', action: 'Prioritizing opportunities', color: '#6366f1' },
  { agent: 'CEO', action: 'Delegating to Sales division', color: '#6366f1' },
  { agent: 'Sales', action: 'Generating outreach strategy', color: '#10b981' },
  { agent: 'Sales', action: 'Created 20 prospect profiles', color: '#10b981' },
  { agent: 'Marketing', action: 'Building campaign assets', color: '#f59e0b' },
  { agent: 'Finance', action: 'Estimating budget: €250,000', color: '#ec4899' },
  { agent: 'Memory', action: 'Storing findings in vector DB', color: '#f97316' },
  { agent: 'Web Intel', action: 'Scraped 200 company profiles', color: '#14b8a6' },
  { agent: 'Operations', action: 'Optimizing workflow pipeline', color: '#8b5cf6' },
]

function AgentNetwork({ agents, executionMode }: { agents: typeof initialAgents, executionMode: boolean }) {
  const [hoveredAgent, setHoveredAgent] = useState<string | null>(null)
  const [packets, setPackets] = useState<{ id: number, from: string, to: string, progress: number, color: string }[]>([])
  const packetRef = useRef(0)

  useEffect(() => {
    const interval = setInterval(() => {
      const conn = connections[Math.floor(Math.random() * connections.length)]
      const fromAgent = agents.find(a => a.id === conn.from)!
      const newPacket = {
        id: packetRef.current++,
        from: conn.from,
        to: conn.to,
        progress: 0,
        color: fromAgent.color
      }
      setPackets(prev => [...prev.slice(-15), newPacket])
    }, executionMode ? 400 : 1200)
    return () => clearInterval(interval)
  }, [executionMode, agents])

  useEffect(() => {
    const interval = setInterval(() => {
      setPackets(prev => prev
        .map(p => ({ ...p, progress: p.progress + (executionMode ? 0.04 : 0.02) }))
        .filter(p => p.progress < 1)
      )
    }, 30)
    return () => clearInterval(interval)
  }, [executionMode])

  const getAgent = (id: string) => agents.find(a => a.id === id)!

  return (
    <div className="relative w-full h-full">
      <svg className="absolute inset-0 w-full h-full" viewBox="0 0 800 520">
        {/* Connection lines */}
        {connections.map((conn, i) => {
          const from = getAgent(conn.from)
          const to = getAgent(conn.to)
          const isActive = executionMode
          return (
            <line key={i}
              x1={from.x} y1={from.y} x2={to.x} y2={to.y}
              stroke={isActive ? 'rgba(99,102,241,0.35)' : 'rgba(99,102,241,0.1)'}
              strokeWidth={isActive ? "1.5" : "1"}
              strokeDasharray="4 4"
            />
          )
        })}

        {/* Data packets */}
        {packets.map(packet => {
          const from = getAgent(packet.from)
          const to = getAgent(packet.to)
          const x = from.x + (to.x - from.x) * packet.progress
          const y = from.y + (to.y - from.y) * packet.progress
          return (
            <g key={packet.id}>
              <circle cx={x} cy={y} r="4" fill={packet.color} opacity={1 - packet.progress} />
              <circle cx={x} cy={y} r="8" fill={packet.color} opacity={(1 - packet.progress) * 0.2} />
            </g>
          )
        })}

        {/* Agent nodes */}
        {agents.map((agent) => {
          const isHovered = hoveredAgent === agent.id
          const statusColor = agentStatusColors[agent.status]
          const isWorking = agent.status === 'thinking' || agent.status === 'executing'

          return (
            <g key={agent.id}
              style={{ cursor: 'pointer' }}
              onMouseEnter={() => setHoveredAgent(agent.id)}
              onMouseLeave={() => setHoveredAgent(null)}
            >
              {/* Outer pulse ring */}
              {isWorking && (
                <circle cx={agent.x} cy={agent.y} r="36" fill="none" stroke={statusColor} strokeWidth="1" opacity="0.5">
                  <animate attributeName="r" values="30;46;30" dur="1.5s" repeatCount="indefinite" />
                  <animate attributeName="opacity" values="0.5;0;0.5" dur="1.5s" repeatCount="indefinite" />
                </circle>
              )}

              {/* Status ring */}
              <circle cx={agent.x} cy={agent.y} r="28"
                fill="none"
                stroke={statusColor}
                strokeWidth="1.5"
                opacity={isWorking ? 1 : 0.4}
              />

              {/* Node body */}
              <circle cx={agent.x} cy={agent.y} r="24"
                fill={isHovered || isWorking ? `${agent.color}30` : `${agent.color}15`}
                stroke={isHovered ? agent.color : `${agent.color}50`}
                strokeWidth={isHovered ? "2" : "1"}
              />

              {/* Glow effect when working */}
              {isWorking && (
                <circle cx={agent.x} cy={agent.y} r="24"
                  fill="none"
                  stroke={agent.color}
                  strokeWidth="3"
                  opacity="0.3"
                  filter="blur(4px)"
                />
              )}

              {/* Icon */}
              <text x={agent.x} y={agent.y - 5} textAnchor="middle" fontSize="14">{agent.icon}</text>
              {/* Name */}
              <text x={agent.x} y={agent.y + 9} textAnchor="middle" fontSize="7.5" fill={agent.color} fontWeight="600">{agent.name}</text>

              {/* Status dot */}
              <circle cx={agent.x + 18} cy={agent.y - 18} r="4" fill={statusColor} />
              {isWorking && (
                <circle cx={agent.x + 18} cy={agent.y - 18} r="4" fill={statusColor}>
                  <animate attributeName="r" values="4;7;4" dur="1s" repeatCount="indefinite" />
                  <animate attributeName="opacity" values="1;0.3;1" dur="1s" repeatCount="indefinite" />
                </circle>
              )}

              {/* Tooltip */}
              {isHovered && (
                <g>
                  <rect x={agent.x + 32} y={agent.y - 60} width="145" height="110" rx="8"
                    fill="rgba(10,12,30,0.97)" stroke={agent.color} strokeWidth="1" />
                  <text x={agent.x + 42} y={agent.y - 40} fontSize="9" fill={agent.color} fontWeight="bold">{agent.name}</text>
                  <text x={agent.x + 42} y={agent.y - 25} fontSize="8" fill={agentStatusColors[agent.status]} fontWeight="600">● {agentStatusLabels[agent.status]}</text>
                  <text x={agent.x + 42} y={agent.y - 10} fontSize="8" fill="#64748b">Tasks: {agent.tasks}</text>
                  <text x={agent.x + 42} y={agent.y + 4} fontSize="8" fill="#64748b">Memory: {agent.memory}%</text>
                  <text x={agent.x + 42} y={agent.y + 18} fontSize="8" fill="#64748b">Messages: {agent.messages}</text>
                  <text x={agent.x + 42} y={agent.y + 32} fontSize="8" fill="#64748b">Success: {agent.success}%</text>
                </g>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}

export default function App() {
  const [task, setTask] = useState('')
  const [sections, setSections] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [agents, setAgents] = useState(initialAgents)
  const [currentAgent, setCurrentAgent] = useState('')
  const [view, setView] = useState<'command' | 'tasks'>('command')
  const [showPalette, setShowPalette] = useState(false)
  const [events, setEvents] = useState(eventTemplates.slice(0, 5))
  const [workflowActive, setWorkflowActive] = useState(0)
  const [executionMode, setExecutionMode] = useState(false)
  const [taskCount, setTaskCount] = useState(124)

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'k') { e.preventDefault(); setShowPalette(prev => !prev) }
      if (e.key === 'Escape') setShowPalette(false)
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [])

  useEffect(() => {
    const interval = setInterval(() => {
      setWorkflowActive(prev => (prev + 1) % workflowSteps.length)
    }, executionMode ? 800 : 2000)
    return () => clearInterval(interval)
  }, [executionMode])

  useEffect(() => {
    const interval = setInterval(() => {
      const template = eventTemplates[Math.floor(Math.random() * eventTemplates.length)]
      setEvents(prev => [{ ...template, time: 'just now' }, ...prev.slice(0, 9)])
    }, executionMode ? 1500 : 4000)
    return () => clearInterval(interval)
  }, [executionMode])

  useEffect(() => {
    if (executionMode) {
      const interval = setInterval(() => {
        setTaskCount(prev => prev + 1)
      }, 2000)
      return () => clearInterval(interval)
    }
  }, [executionMode])

  const setAgentStatus = (id: string, status: AgentStatus) => {
    setAgents(prev => prev.map(a => a.id === id ? { ...a, status } : a))
  }

  const runTask = async () => {
    if (!task) return
    setLoading(true)
    setSections([])
    setExecutionMode(true)
    setView('tasks')

    const agentSequence = [
      { id: 'ceo', status: 'thinking' as AgentStatus },
      { id: 'research', status: 'executing' as AgentStatus },
      { id: 'web', status: 'executing' as AgentStatus },
      { id: 'sales', status: 'executing' as AgentStatus },
      { id: 'marketing', status: 'executing' as AgentStatus },
      { id: 'finance', status: 'executing' as AgentStatus },
      { id: 'ops', status: 'executing' as AgentStatus },
      { id: 'memory', status: 'executing' as AgentStatus },
    ]

    for (const { id, status } of agentSequence) {
      setAgentStatus(id, status)
      setCurrentAgent(agents.find(a => a.id === id)?.name || '')
      await new Promise(r => setTimeout(r, 400))
    }

    try {
      const res = await fetch('https://enterprise-ai-os-1.onrender.com/tasks/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: task, description: task })
      })
      const data = await res.json()
      if (data.result) setSections(data.result.split('---').map((s: string) => s.trim()).filter(Boolean))
    } catch (e) {
      setSections(['❌ Error connecting to backend'])
    }

    // Set all to completed
    agentSequence.forEach(({ id }) => setAgentStatus(id, 'completed'))
    await new Promise(r => setTimeout(r, 1000))
    agentSequence.forEach(({ id }) => setAgentStatus(id, 'idle'))

    setExecutionMode(false)
    setCurrentAgent('')
    setLoading(false)
  }

  return (
    <div className="min-h-screen text-white overflow-hidden" style={{ background: executionMode ? '#060918' : '#050816', transition: 'background 1s ease' }}>
      <NeuralBackground />

      {/* Execution Mode Overlay */}
      <AnimatePresence>
        {executionMode && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-0 pointer-events-none"
            style={{ background: 'radial-gradient(ellipse at center, rgba(99,102,241,0.05) 0%, transparent 70%)' }}
          />
        )}
      </AnimatePresence>

      {/* TOP BAR */}
      <div className="border-b border-white/5 px-6 py-3 flex items-center justify-between sticky top-0 z-50"
        style={{ background: 'rgba(5,8,22,0.95)', backdropFilter: 'blur(20px)' }}>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <motion.div animate={{ rotate: executionMode ? 360 : 0 }} transition={{ repeat: executionMode ? Infinity : 0, duration: 3, ease: 'linear' }}
              className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold"
              style={{ background: 'linear-gradient(135deg, #6366f1, #00E5FF)' }}>⚡</motion.div>
            <span className="font-bold text-sm" style={{ background: 'linear-gradient(90deg, #6366f1, #00E5FF)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              Enterprise AI OS
            </span>
          </div>
          <motion.div animate={{ borderColor: executionMode ? 'rgba(99,102,241,0.5)' : 'rgba(16,185,129,0.2)' }}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border"
            style={{ background: executionMode ? 'rgba(99,102,241,0.1)' : 'rgba(16,185,129,0.1)' }}>
            <motion.div animate={{ scale: executionMode ? [1, 1.5, 1] : 1 }} transition={{ repeat: Infinity, duration: 1 }}
              className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: executionMode ? '#6366f1' : '#10b981' }} />
            <span className="text-xs" style={{ color: executionMode ? '#818cf8' : '#4ade80' }}>
              {executionMode ? 'EXECUTING' : 'SYSTEM ONLINE'}
            </span>
          </motion.div>
        </div>

        {/* Live Metrics */}
        <div className="flex items-center gap-8">
          {[
            { label: 'Agents', value: '8 Active', color: '#6366f1' },
            { label: 'Tasks', value: `${taskCount} Running`, color: '#10b981' },
            { label: 'Latency', value: '142ms', color: '#06b6d4' },
            { label: 'Health', value: '99.9%', color: '#f59e0b' },
          ].map((stat, i) => (
            <div key={i} className="text-center">
              <motion.div animate={{ color: executionMode ? '#ffffff' : stat.color }}
                className="text-xs font-bold">{stat.value}</motion.div>
              <div className="text-xs text-gray-600">{stat.label}</div>
            </div>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <button onClick={() => setView('command')}
            className={`text-xs px-3 py-1.5 rounded-lg transition-all ${view === 'command' ? 'bg-indigo-600 text-white' : 'text-gray-500 hover:text-gray-300'}`}>
            Command Center
          </button>
          <button onClick={() => setView('tasks')}
            className={`text-xs px-3 py-1.5 rounded-lg transition-all ${view === 'tasks' ? 'bg-indigo-600 text-white' : 'text-gray-500 hover:text-gray-300'}`}>
            Run Task
          </button>
          <button onClick={() => setShowPalette(true)}
            className="text-xs px-2 py-1.5 rounded-lg border border-white/10 text-gray-500 hover:text-gray-300">⌘K</button>
        </div>
      </div>

      <AnimatePresence mode="wait">
        {view === 'command' ? (
          <motion.div key="command" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="flex" style={{ height: 'calc(100vh - 57px)' }}>

            {/* LEFT PANEL */}
            <div className="w-52 border-r border-white/5 p-4 flex-shrink-0 overflow-y-auto"
              style={{ background: 'rgba(5,8,22,0.85)' }}>
              <p className="text-xs text-gray-600 uppercase tracking-widest mb-3 font-semibold">Organization</p>
              <div className="space-y-1 mb-6">
                <div className="flex items-center gap-2 px-2 py-2 rounded-lg" style={{ background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.2)' }}>
                  <span>👔</span>
                  <span className="text-xs font-semibold text-indigo-400">CEO Agent</span>
                  <div className="ml-auto w-1.5 h-1.5 rounded-full" style={{ backgroundColor: agentStatusColors[agents.find(a => a.id === 'ceo')?.status || 'idle'] }} />
                </div>
                {agents.filter(a => a.id !== 'ceo').map((agent, i) => (
                  <motion.div key={i} whileHover={{ x: 4 }}
                    className="flex items-center gap-2 px-2 py-1.5 rounded-lg ml-2 cursor-pointer transition-all hover:bg-white/5">
                    <span className="text-gray-700 text-xs">├</span>
                    <span className="text-sm">{agent.icon}</span>
                    <span className="text-xs" style={{ color: agent.color }}>{agent.name}</span>
                    <motion.div animate={{ backgroundColor: agentStatusColors[agent.status] }}
                      className="ml-auto w-1.5 h-1.5 rounded-full" />
                  </motion.div>
                ))}
              </div>

              {/* Task Input */}
              <div className="border-t border-white/5 pt-4">
                <p className="text-xs text-gray-600 uppercase tracking-widest mb-2 font-semibold">Execute Task</p>
                <textarea
                  className="w-full rounded-lg px-3 py-2 text-white outline-none text-xs placeholder-gray-700 border border-white/5 focus:border-indigo-500 transition-colors resize-none"
                  style={{ background: 'rgba(15,23,42,0.8)' }}
                  placeholder="Enter task for CEO Agent..."
                  rows={3}
                  value={task}
                  onChange={e => setTask(e.target.value)}
                />
                <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                  onClick={runTask} disabled={loading}
                  className="w-full mt-2 py-2 rounded-lg text-xs font-semibold disabled:opacity-50 transition-all"
                  style={{ background: loading ? 'rgba(99,102,241,0.5)' : 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}>
                  {loading ? '⚡ Executing...' : '▶ Execute'}
                </motion.button>
              </div>

              {/* Agent Status Legend */}
              <div className="mt-4 border-t border-white/5 pt-4">
                <p className="text-xs text-gray-600 uppercase tracking-widest mb-2 font-semibold">Status</p>
                {Object.entries(agentStatusLabels).map(([status, label]) => (
                  <div key={status} className="flex items-center gap-2 mb-1">
                    <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: agentStatusColors[status as AgentStatus] }} />
                    <span className="text-xs text-gray-600">{label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* CENTER */}
            <div className="flex-1 flex flex-col min-w-0">
              <div className="flex-1 relative">
                <div className="absolute top-4 left-4 z-10">
                  <span className="text-xs text-gray-600 uppercase tracking-widest">Live Agent Network</span>
                  {executionMode && (
                    <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                      className="ml-3 text-xs text-indigo-400 font-semibold">
                      ⚡ {currentAgent} working...
                    </motion.span>
                  )}
                </div>
                <AgentNetwork agents={agents} executionMode={executionMode} />
              </div>

              {/* WORKFLOW */}
              <div className="border-t border-white/5 px-6 py-4" style={{ background: 'rgba(5,8,22,0.85)' }}>
                <p className="text-xs text-gray-600 uppercase tracking-widest mb-3">Active Workflow</p>
                <div className="flex items-center gap-2 overflow-x-auto">
                  {workflowSteps.map((step, i) => (
                    <div key={i} className="flex items-center gap-2 flex-shrink-0">
                      <motion.div
                        animate={{
                          scale: workflowActive === i ? 1.1 : 1,
                          opacity: workflowActive === i ? 1 : 0.35,
                          boxShadow: workflowActive === i ? `0 0 12px ${step.color}40` : 'none'
                        }}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold"
                        style={{
                          borderColor: workflowActive === i ? step.color : 'rgba(255,255,255,0.05)',
                          background: workflowActive === i ? `${step.color}20` : 'transparent',
                          color: workflowActive === i ? step.color : '#4b5563'
                        }}
                      >
                        <span>{step.icon}</span>{step.label}
                      </motion.div>
                      {i < workflowSteps.length - 1 && (
                        <motion.span animate={{ color: workflowActive === i ? '#6366f1' : '#1f2937', scale: workflowActive === i ? 1.2 : 1 }}
                          className="text-xs">→</motion.span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* RIGHT PANEL */}
            <div className="w-64 border-l border-white/5 p-4 flex-shrink-0 overflow-y-auto"
              style={{ background: 'rgba(5,8,22,0.85)' }}>
              <div className="flex items-center justify-between mb-4">
                <p className="text-xs text-gray-600 uppercase tracking-widest font-semibold">Live Activity</p>
                <motion.div animate={{ scale: executionMode ? [1, 1.3, 1] : 1 }} transition={{ repeat: Infinity, duration: 1 }}
                  className="w-1.5 h-1.5 rounded-full bg-green-500" />
              </div>
              <div className="space-y-2">
                <AnimatePresence mode="popLayout">
                  {events.slice(0, 8).map((event, i) => (
                    <motion.div key={`${event.agent}-${event.action}-${i}`}
                      initial={{ opacity: 0, y: -20, scale: 0.95 }}
                      animate={{ opacity: 1 - i * 0.08, y: 0, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.9 }}
                      transition={{ duration: 0.3 }}
                      className="p-2.5 rounded-xl border border-white/5"
                      style={{ background: i === 0 ? `${event.color}10` : 'rgba(15,23,42,0.4)', borderColor: i === 0 ? `${event.color}30` : 'rgba(255,255,255,0.05)' }}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: event.color }} />
                        <span className="text-xs font-semibold" style={{ color: event.color }}>{event.agent}</span>
                        {i === 0 && <span className="text-xs text-gray-700 ml-auto">now</span>}
                      </div>
                      <p className="text-xs leading-relaxed" style={{ color: i === 0 ? '#94a3b8' : '#4b5563' }}>{event.action}</p>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </div>
          </motion.div>

        ) : (
          <motion.div key="tasks" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="max-w-5xl mx-auto p-6 relative z-10">

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

            {/* Agent Status Grid */}
            <div className="grid grid-cols-4 gap-3 mb-6">
              {agents.map((agent, i) => (
                <motion.div key={i}
                  animate={{ borderColor: agent.status !== 'idle' ? agent.color : 'rgba(255,255,255,0.05)' }}
                  className="rounded-xl p-3 border transition-all"
                  style={{ background: agent.status !== 'idle' ? `${agent.color}10` : 'rgba(15,23,42,0.65)' }}>
                  <div className="flex items-center gap-2">
                    <span className="text-sm">{agent.icon}</span>
                    <p className="text-xs font-semibold truncate flex-1">{agent.name}</p>
                    <motion.div className="w-2 h-2 rounded-full flex-shrink-0"
                      style={{ backgroundColor: agentStatusColors[agent.status] }}
                      animate={{ scale: agent.status !== 'idle' ? [1, 1.4, 1] : 1 }}
                      transition={{ repeat: agent.status !== 'idle' ? Infinity : 0, duration: 0.8 }} />
                  </div>
                  <p className="text-xs mt-1" style={{ color: agentStatusColors[agent.status] }}>
                    {agentStatusLabels[agent.status]}
                  </p>
                  {agent.status === 'executing' && (
                    <motion.div initial={{ width: 0 }} animate={{ width: '100%' }}
                      transition={{ duration: 2, repeat: Infinity }}
                      className="h-0.5 rounded-full mt-2" style={{ backgroundColor: agent.color }} />
                  )}
                </motion.div>
              ))}
            </div>

            {/* Loading */}
            <AnimatePresence>
              {loading && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                  className="rounded-2xl p-8 border border-indigo-500/20 mb-6 text-center"
                  style={{ background: 'rgba(99,102,241,0.05)' }}>
                  <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1.5, ease: 'linear' }}
                    className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full mx-auto mb-4" />
                  <p className="text-gray-300 text-sm font-semibold">{currentAgent ? `${currentAgent} is working...` : 'Initializing agents...'}</p>
                  <p className="text-gray-600 text-xs mt-1">All 8 agents collaborating in real-time</p>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Results */}
            {sections.length > 0 && (
              <div className="space-y-4">
                {sections.map((section, i) => (
                  <motion.div key={i} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}
                    className="rounded-2xl p-6 border border-white/5"
                    style={{ background: 'rgba(15,23,42,0.65)' }}>
                    <div className="text-sm text-gray-300 leading-relaxed prose prose-invert prose-sm max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{section}</ReactMarkdown>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}

            {!loading && sections.length === 0 && (
              <div className="text-center py-20">
                <motion.div animate={{ rotate: [0, 10, -10, 0] }} transition={{ repeat: Infinity, duration: 4 }}
                  className="text-6xl mb-4">⚡</motion.div>
                <h2 className="text-xl font-semibold text-gray-500 mb-2">Mission Control Ready</h2>
                <p className="text-gray-700 text-sm">Type a business task — all 8 agents will collaborate autonomously</p>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Command Palette */}
      <AnimatePresence>
        {showPalette && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-start justify-center pt-32"
            style={{ background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(12px)' }}
            onClick={() => setShowPalette(false)}>
            <motion.div initial={{ opacity: 0, scale: 0.95, y: -20 }} animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -20 }}
              className="w-full max-w-lg rounded-2xl border border-white/10 overflow-hidden"
              style={{ background: 'rgba(10,12,30,0.98)' }}
              onClick={e => e.stopPropagation()}>
              <div className="flex items-center gap-3 px-4 py-3 border-b border-white/5">
                <span className="text-gray-500 text-sm">⌘</span>
                <input autoFocus
                  className="flex-1 bg-transparent text-white outline-none text-sm placeholder-gray-600"
                  placeholder="Search agents, tasks, commands..." />
                <span className="text-xs text-gray-600 px-2 py-1 rounded border border-white/10">ESC</span>
              </div>
              <div className="p-2">
                {[
                  { icon: '🖥️', label: 'Command Center', desc: 'View live agent network', action: () => { setView('command'); setShowPalette(false) } },
                  { icon: '▶', label: 'Run New Task', desc: 'Delegate to CEO Agent', action: () => { setView('tasks'); setShowPalette(false) } },
                  { icon: '🤖', label: 'Agent Network', desc: 'View all agent connections', action: () => { setView('command'); setShowPalette(false) } },
                  { icon: '📊', label: 'View Reports', desc: 'See completed task reports', action: () => { setView('tasks'); setShowPalette(false) } },
                ].map((cmd, i) => (
                  <motion.button key={i} whileHover={{ backgroundColor: 'rgba(255,255,255,0.05)' }}
                    onClick={cmd.action}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-all">
                    <span className="text-lg">{cmd.icon}</span>
                    <div>
                      <p className="text-sm text-gray-200 font-medium">{cmd.label}</p>
                      <p className="text-xs text-gray-600">{cmd.desc}</p>
                    </div>
                  </motion.button>
                ))}
              </div>
              <div className="px-4 py-2 border-t border-white/5 flex justify-between">
                <span className="text-xs text-gray-700">Ctrl+K to toggle</span>
                <span className="text-xs text-gray-700">ESC to close</span>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}