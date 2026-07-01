import { AnimatePresence, motion } from 'framer-motion'

export type AgentMessage = {
  id: string
  agent: string
  timestamp: string
  message: string
  priority?: 'info' | 'warning' | 'success'
}

export default function ConversationTimeline({ messages }: { messages: AgentMessage[] }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-slate-950/60 p-5 shadow-2xl shadow-slate-950/20 backdrop-blur-xl">
      <div className="flex items-start justify-between gap-4 pb-4 border-b border-white/10 mb-5">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-cyan-300 font-semibold">Live Conversation</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">Agent Timeline</h2>
        </div>
        <span className="rounded-full border border-slate-700/80 bg-slate-900/80 px-3 py-1 text-xs text-slate-300">Real-time feed</span>
      </div>

      <div className="space-y-4">
        <AnimatePresence initial={false} mode="popLayout">
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
              className="rounded-3xl border border-white/5 bg-slate-900/90 p-4"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-2xl bg-slate-800/80 border border-white/10 flex items-center justify-center text-lg text-sky-300 font-semibold">
                    {message.agent.charAt(0)}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white">{message.agent}</p>
                    <p className="text-xs text-slate-500">{message.timestamp}</p>
                  </div>
                </div>
                <span className={`rounded-full px-2 py-1 text-[11px] font-semibold ${
                  message.priority === 'warning'
                    ? 'bg-amber-500/15 text-amber-300'
                    : message.priority === 'success'
                    ? 'bg-emerald-500/15 text-emerald-300'
                    : 'bg-slate-700/50 text-slate-300'
                }`}
                >
                  {message.priority === 'warning' ? 'Alert' : message.priority === 'success' ? 'Update' : 'Info'}
                </span>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-300">{message.message}</p>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  )
}
