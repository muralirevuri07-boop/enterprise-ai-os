import { motion } from 'framer-motion'
import { Download, FileCheck2, FileReport, ShieldCheck, TrendingUp, Zap } from 'lucide-react'

export type ReportSection = {
  title: string
  content: string
  accent: string
}

export type ReportData = {
  summary: string
  objective: string
  keyFindings: string[]
  financialAnalysis: string
  risks: string[]
  recommendations: string[]
  ceoDecision: string
  highlights: Array<{ label: string; value: string }>
}

export default function ExecutiveReport({ report, onDownload }: { report: ReportData; onDownload: (type: 'PDF' | 'DOCX' | 'JSON') => void }) {
  const sectionCards: ReportSection[] = [
    { title: 'Executive Summary', content: report.summary, accent: '#38bdf8' },
    { title: 'Mission Objective', content: report.objective, accent: '#a78bfa' },
    { title: 'Financial Analysis', content: report.financialAnalysis, accent: '#f472b6' },
    { title: 'CEO Final Decision', content: report.ceoDecision, accent: '#22c55e' },
  ]

  return (
    <div className="rounded-3xl border border-white/10 bg-slate-950/60 p-5 shadow-2xl shadow-slate-950/20 backdrop-blur-xl">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between pb-4 border-b border-white/10 mb-5">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-fuchsia-400 font-semibold">Executive Report</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">Boardroom Briefing</h2>
        </div>
        <div className="flex flex-wrap gap-3">
          {(['PDF', 'DOCX', 'JSON'] as const).map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => onDownload(type)}
              className="inline-flex items-center gap-2 rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-2 text-sm font-semibold text-slate-100 transition hover:border-slate-200/20 hover:bg-slate-800"
            >
              <Download className="h-4 w-4" />
              {type}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-4">
          {sectionCards.map((section) => (
            <motion.div
              key={section.title}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="rounded-3xl border border-white/5 bg-slate-900/90 p-5"
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-100">{section.title}</p>
                  <div className="mt-1 h-1 rounded-full" style={{ background: section.accent }} />
                </div>
                <div className="rounded-2xl bg-slate-950/80 px-3 py-1 text-xs uppercase tracking-[0.24em] text-slate-400">Live</div>
              </div>
              <p className="mt-4 text-sm leading-7 text-slate-300">{section.content}</p>
            </motion.div>
          ))}
        </div>

        <div className="space-y-4">
          <motion.div className="rounded-3xl border border-white/5 bg-slate-900/90 p-5" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <div className="flex items-center gap-3 text-slate-100">
              <FileReport className="h-5 w-5 text-cyan-400" />
              <p className="text-sm font-semibold">Key Findings</p>
            </div>
            <ul className="mt-4 space-y-2 text-sm text-slate-300">
              {report.keyFindings.map((finding, index) => (
                <li key={index} className="rounded-2xl border border-slate-800/80 bg-slate-950/80 p-3">
                  <p>{finding}</p>
                </li>
              ))}
            </ul>
          </motion.div>

          <motion.div className="rounded-3xl border border-white/5 bg-slate-900/90 p-5" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <div className="flex items-center gap-3 text-slate-100">
              <ShieldCheck className="h-5 w-5 text-amber-400" />
              <p className="text-sm font-semibold">Risks</p>
            </div>
            <ul className="mt-4 space-y-2 text-sm text-slate-300">
              {report.risks.map((risk, index) => (
                <li key={index} className="rounded-2xl border border-slate-800/80 bg-slate-950/80 p-3">
                  <p>{risk}</p>
                </li>
              ))}
            </ul>
          </motion.div>

          <motion.div className="rounded-3xl border border-white/5 bg-slate-900/90 p-5" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <div className="flex items-center gap-3 text-slate-100">
              <FileCheck2 className="h-5 w-5 text-emerald-400" />
              <p className="text-sm font-semibold">Recommendations</p>
            </div>
            <ul className="mt-4 space-y-2 text-sm text-slate-300">
              {report.recommendations.map((item, index) => (
                <li key={index} className="rounded-2xl border border-slate-800/80 bg-slate-950/80 p-3">
                  <p>{item}</p>
                </li>
              ))}
            </ul>
          </motion.div>
        </div>
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        {report.highlights.map((highlight) => (
          <div key={highlight.label} className="rounded-3xl border border-white/5 bg-slate-900/90 p-4">
            <p className="text-xs uppercase tracking-[0.22em] text-slate-400">{highlight.label}</p>
            <p className="mt-2 text-2xl font-semibold text-white">{highlight.value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
