import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { ScrapingJob } from '../types/api'

interface JobState {
  jobs: ScrapingJob[]
  activeJobs: ScrapingJob[]
  jobLogs: Record<string, JobLog[]>

  setJobs: (jobs: ScrapingJob[]) => void
  addJob: (job: ScrapingJob) => void
  updateJob: (id: string, updates: Partial<ScrapingJob>) => void
  deleteJob: (id: string) => void
  setActiveJobs: (jobs: ScrapingJob[]) => void
  addJobLog: (jobId: string, log: JobLog) => void
  clearJobLogs: (jobId: string) => void
}

interface JobLog {
  id: string
  timestamp: string
  level: 'info' | 'warning' | 'error' | 'success'
  message: string
  details?: Record<string, unknown>
}

export const useJobStore = create<JobState>()(
  devtools(
    set => ({
      jobs: [],
      activeJobs: [],
      jobLogs: {},

      setJobs: jobs => set({ jobs }),

      addJob: job => set(state => ({ jobs: [...state.jobs, job] })),

      updateJob: (id, updates) =>
        set(state => ({
          jobs: state.jobs.map(job => (job.job_id === id ? { ...job, ...updates } : job)),
          activeJobs: state.activeJobs.map(job =>
            job.job_id === id ? { ...job, ...updates } : job
          ),
        })),

      deleteJob: id =>
        set(state => ({
          jobs: state.jobs.filter(job => job.job_id !== id),
          activeJobs: state.activeJobs.filter(job => job.job_id !== id),
        })),

      setActiveJobs: jobs => set({ activeJobs: jobs }),

      addJobLog: (jobId, log) =>
        set(state => ({
          jobLogs: {
            ...state.jobLogs,
            [jobId]: [...(state.jobLogs[jobId] || []), log],
          },
        })),

      clearJobLogs: jobId =>
        set(state => ({
          jobLogs: {
            ...state.jobLogs,
            [jobId]: [],
          },
        })),
    }),
    {
      name: 'job-store',
    }
  )
)
