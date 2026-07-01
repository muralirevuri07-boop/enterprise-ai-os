import { motion } from 'framer-motion'
import { Cpu, ShieldCheck, TrendingUp, Sparkle, Database, Users2, Megaphone } from 'lucide-react'

export type AgentStatus = 'idle' | 'active' | 'waiting' | 'complete'

export type AgentNode = {
  id: string
  name: string
  role: string
  color: string
  icon: string
  status: AgentStatus
  x: number
  y: number
}

const statusLabels: Record<AgentStatus, string> = {
  idle: 'Idle',
  active: 'Active',
  waiting: 'Waiting',
  complete: 'Complete',
}

const statusColors: Record<AgentStatus, string> = {
  idle: '#94a3b8',
  active: '#60a5fa',
  waiting: '#fbbf24',
  complete: '#34d399',
}

const iconMap: Record<string, JSX.Element> = {
  CEO: <Users2 className="h-4 w-4" />,
  Research: <Sparkle className="h-4 w-4" />,
  Finance: <TrendingUp className="h-4 w-4" />,
  Marketing: <Megaphone className="h-4 w-4" />,
  Operations: <Cpu className="h-4 w-4" />,
  Memory: <Database className="h-4 w-4" />,
  Governance: <ShieldCheck className="h-4 w-4" />,
}

const links = [
  ['ceo', 'research'],
  ['ceo', 'finance'],
  ['ceo', 'marketing'],
  ['ceo', 'operations'],
  ['ceo', 'memory'],
  ['ceo', 'governance'],
  ['research', 'memory'],
  ['marketing', 'finance'],
  ['operations', 'memory'],
  ['finance', 'governance'],
]

export default function AgentNetwork({ agents, activeAgent }: { agents: AgentNode[]; activeAgent?: string }) {
  const getAgent = (id: string) => agents.find((agent) => agent.id === id)!

  return (
    <div className="rounded-3xl border border-white/10 bg-slate-950/60 p-5 shadow-2xl shadow-slate-950/20 backdrop-blur-xl">
      <div className="flex items-start justify-between gap-4 pb-4 border-b border-white/10 mb-5">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-sky-400 font-semibold">Live Agent Network</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">Mission Control Nodes</h2>
        </div>
        <span className="rounded-full border border-slate-700/80 bg-slate-900/80 px-3 py-1 text-xs text-slate-300">7 agents online</span>
      </div>

      <div className="relative overflow-hidden rounded-3xl border border-slate-900/80 bg-slate-950/80 p-4">
        <svg viewBox="0 0 680 320" className="h-[300px] w-full">
          {links.map(([from, to], index) => {
            const source = getAgent(from)
            const target = getAgent(to)
            return (
              <line
                key={index}
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                stroke="rgba(148,163,184,0.28)"
                strokeWidth="1"
                strokeDasharray="4 4"
              />
            )
          })}

          {agents.map((agent) => {
            const isActive = agent.id === activeAgent
            const statusColor = statusColors[agent.status]
            return (
              <g key={agent.id}>
                <motion.circle
                  cx={agent.x}
                  cy={agent.y}
                  r={isActive ? 32 : 26}
                  fill={agent.color}
                  opacity={isActive ? 0.18 : 0.1}
                  animate={{ scale: isActive ? [1, 1.06, 1] : 1 }}
                  transition={{ duration: 2, repeat: isActive ? Infinity : 0 }}
                />
                <circle cx={agent.x} cy={agent.y} r="22" fill="#0f172a" stroke={statusColor} strokeWidth="2" />
                <text x={agent.x} y={agent.y + 6} textAnchor="middle" fontSize="13" fill={statusColor} fontWeight="700">{agent.icon}</text>
                <text x={agent.x} y={agent.y + 46} textAnchor="middle" fontSize="11" fill="#94a3b8">{agent.name}</text>
              </g>
            )
          })}
        </svg>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {agents.map((agent) => (
          <motion.div
            key={agent.id}
            className="rounded-3xl border border-white/5 bg-slate-950/90 p-4"
            whileHover={{ y: -2 }}
          >
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-900/70 text-sky-400">
                {iconMap[agent.name] ?? <Sparkle className="h-4 w-4" />}
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-white">{agent.name}</p>
                <p className="text-[11px] uppercase tracking-[0.2em] text-slate-500">{agent.role}</p>
              </div>
              <span className="ml-auto h-2.5 w-2.5 rounded-full" style={{ backgroundColor: statusColor }} />
            </div>
            <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
              <span>{statusLabels[agent.status]}</span>
              <span>{agent.status === 'complete' ? 'Ready' : agent.status === 'active' ? 'Processing' : 'Queued'}</span>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
