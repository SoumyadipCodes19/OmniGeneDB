import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  Activity, Play, List, CheckCircle, XCircle, Trash2, RotateCw, 
  AlertOctagon, HelpCircle, BarChart3, AlertCircle 
} from 'lucide-react'
import ForceGraph2D from 'react-force-graph-2d'
import { BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip, Legend, ResponsiveContainer } from 'recharts'
import { ErrorBoundary } from '@/components/ErrorBoundary'

const API_URL = (typeof window !== 'undefined' && (window as any).__ENV__?.API_URL) || import.meta.env.VITE_API_URL || ''

function App() {
  const [activeTab, setActiveTab] = useState<'submit' | 'history'>('submit')
  const [currentRunId, setCurrentRunId] = useState<string | null>(null)

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white shadow-sm border-b px-6 py-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-blue-700 flex items-center gap-2">
            <Activity className="h-6 w-6" /> OmniGeneDB
          </h1>
          <p className="text-sm text-gray-500">Automated Multi-Database Gene Profiling Pipeline</p>
        </div>
        <nav className="flex gap-4">
          <button 
            onClick={() => setActiveTab('submit')}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${activeTab === 'submit' ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:bg-gray-100'}`}
          >
            Submit Run
          </button>
          <button 
            onClick={() => setActiveTab('history')}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${activeTab === 'history' ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:bg-gray-100'}`}
          >
            Runs History
          </button>
        </nav>
      </header>

      <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
        {activeTab === 'submit' && (
          <ErrorBoundary>
            <SubmitRunView onRunSubmitted={(id) => {
              setCurrentRunId(id)
              setActiveTab('history')
            }} />
          </ErrorBoundary>
        )}
        {activeTab === 'history' && (
          <ErrorBoundary>
            <RunsHistoryView currentRunId={currentRunId} onSelectRun={setCurrentRunId} />
          </ErrorBoundary>
        )}
      </main>
    </div>
  )
}

function SubmitRunView({ onRunSubmitted }: { onRunSubmitted: (id: string) => void }) {
  const [accession, setAccession] = useState('')
  const [caseGroup, setCaseGroup] = useState('')
  const [controlGroup, setControlGroup] = useState('')
  const [topN, setTopN] = useState(50)
  const [isCancer, setIsCancer] = useState(false)
  const [suggestedGroups, setSuggestedGroups] = useState<any>(null)
  const [isFetchingGroups, setIsFetchingGroups] = useState(false)
  const [groupError, setGroupError] = useState('')

  const handleFetchGroups = async () => {
    if (!accession) return
    setIsFetchingGroups(true)
    setGroupError('')
    setSuggestedGroups(null)
    try {
      const res = await fetch(`${API_URL}/geo/groups/${accession}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      if (data.error) setGroupError(data.error)
      else setSuggestedGroups(data.suggested_groups)
    } catch {
      setGroupError("Failed to fetch groups")
    }
    setIsFetchingGroups(false)
  }

  const mutation = useMutation({
    mutationFn: async (data: any) => {
      const res = await fetch(`${API_URL}/runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })
      if (!res.ok) throw new Error("Failed to submit")
      return res.json()
    },
    onSuccess: (data) => {
      onRunSubmitted(data.id)
    }
  })

  return (
    <div className="bg-white p-8 rounded-lg shadow-sm border max-w-2xl mx-auto mt-10">
      <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
        <Play className="h-5 w-5 text-blue-600" /> Start New Pipeline Run
      </h2>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">GEO Accession</label>
          <div className="flex gap-2">
            <input 
              type="text" 
              placeholder="e.g. GSE244435" 
              className="flex-1 p-2 border rounded-md"
              value={accession}
              onChange={e => setAccession(e.target.value)}
            />
            <button 
              onClick={handleFetchGroups}
              disabled={isFetchingGroups || !accession}
              className="bg-gray-100 hover:bg-gray-200 text-gray-800 px-4 py-2 rounded-md font-medium disabled:opacity-50 border transition-colors"
            >
              {isFetchingGroups ? 'Scanning...' : 'Scan Groups'}
            </button>
          </div>
          {groupError && <p className="text-xs text-red-500 mt-1">{groupError}</p>}
        </div>

        {suggestedGroups && Object.keys(suggestedGroups).length > 0 && (
          <div className="bg-gray-50 p-4 rounded-md border text-sm">
            <p className="font-semibold text-gray-700 mb-2">Detected Experimental Variables:</p>
            <div className="space-y-3">
              {Object.entries(suggestedGroups).map(([key, values]: [string, any]) => (
                <div key={key}>
                  <span className="text-gray-500 text-xs uppercase tracking-wider">{key}:</span>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {Array.isArray(values) && values.map((v: string) => (
                      <button
                        key={v}
                        onClick={() => {
                          if (!caseGroup || (caseGroup && controlGroup)) { setCaseGroup(v); setControlGroup(''); }
                          else if (!controlGroup) { setControlGroup(v); }
                        }}
                        className="px-2 py-1 bg-white border border-gray-300 rounded text-gray-700 hover:bg-blue-50 hover:border-blue-300 hover:text-blue-700 transition-colors"
                      >
                        {v}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-400 mt-3 italic">Click buttons to auto-fill Case & Control boxes below.</p>
          </div>
        )}
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Case Group Label</label>
            <input 
              type="text" 
              placeholder="e.g. ko" 
              className="w-full p-2 border rounded-md"
              value={caseGroup}
              onChange={e => setCaseGroup(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Control Group Label</label>
            <input 
              type="text" 
              placeholder="e.g. wt" 
              className="w-full p-2 border rounded-md"
              value={controlGroup}
              onChange={e => setControlGroup(e.target.value)}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Number of Top DEGs to Analyze</label>
          <input 
            type="number" 
            min="1" 
            max="500"
            className="w-full p-2 border rounded-md"
            value={topN}
            onChange={e => setTopN(parseInt(e.target.value) || 50)}
          />
          <p className="text-xs text-gray-500 mt-1">Note: High numbers will take longer to fetch from external databases.</p>
        </div>

        <div>
          <label className="flex items-center space-x-2 text-sm font-medium text-gray-700 mb-4 cursor-pointer">
            <input 
              type="checkbox" 
              className="rounded text-blue-600 border-gray-300 focus:ring-blue-500" 
              checked={isCancer} 
              onChange={e => setIsCancer(e.target.checked)} 
            />
            <span>Is this a Cancer dataset? (Enables TCGA Survival Analysis)</span>
          </label>
        </div>
        
        <button 
          onClick={() => mutation.mutate({ accession, case_group: caseGroup, control_group: controlGroup, top_n: topN, is_cancer: isCancer })}
          disabled={mutation.isPending || !accession || !caseGroup || !controlGroup}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md disabled:opacity-50 mt-4 shadow-sm transition-colors"
        >
          {mutation.isPending ? 'Submitting...' : 'Submit to Pipeline'}
        </button>
      </div>
    </div>
  )
}

function RunsHistoryView({ currentRunId, onSelectRun }: { currentRunId: string | null, onSelectRun: (id: string) => void }) {
  const queryClient = useQueryClient()
  
  const { data: runs, isLoading, isError, error } = useQuery({
    queryKey: ['runs'],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/runs`)
      if (!res.ok) throw new Error(`HTTP error ${res.status}: Failed to load runs`)
      return res.json()
    },
    refetchInterval: 5000 // Poll every 5s
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await fetch(`${API_URL}/runs/${id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error("Failed to delete")
      return id
    },
    onSuccess: (deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['runs'] })
      if (currentRunId === deletedId) onSelectRun('')
    }
  })

  const resubmitMutation = useMutation({
    mutationFn: async (run: any) => {
      const res = await fetch(`${API_URL}/runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          accession: run.accession,
          case_group: run.case_group,
          control_group: run.control_group,
          top_n: run.top_n || 50
        })
      })
      if (!res.ok) throw new Error("Failed to resubmit")
      return res.json()
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['runs'] })
      onSelectRun(data.id)
    }
  })

  const runsList = Array.isArray(runs) ? runs : []

  return (
    <div className="grid grid-cols-12 gap-6 h-[calc(100vh-140px)]">
      <div className="col-span-4 bg-white border rounded-lg shadow-sm overflow-hidden flex flex-col">
        <div className="p-4 border-b bg-gray-50 flex justify-between items-center">
          <h2 className="font-semibold flex items-center gap-2"><List className="h-4 w-4" /> All Runs</h2>
          <span className="text-xs text-gray-500 bg-gray-200 px-2 py-0.5 rounded-full font-medium">
            {runsList.length}
          </span>
        </div>
        <div className="overflow-y-auto flex-1 p-2 space-y-2">
          {isLoading && (
            <div className="p-8 text-center text-sm text-gray-500">
              <RotateCw className="h-5 w-5 animate-spin mx-auto mb-2 text-blue-500" />
              Loading runs...
            </div>
          )}

          {isError && (
            <div className="p-4 bg-red-50 text-red-700 border border-red-200 rounded-md text-xs">
              <p className="font-semibold mb-1">Failed to fetch runs</p>
              <p className="text-red-600">{(error as Error)?.message || 'Network error'}</p>
            </div>
          )}

          {!isLoading && !isError && runsList.length === 0 && (
            <div className="p-8 text-center text-sm text-gray-400">
              No runs recorded yet. Submit a dataset above to start analysis.
            </div>
          )}

          {runsList.map((run: any) => (
            <div 
              key={run.id}
              onClick={() => onSelectRun(run.id)}
              className={`group p-3 border rounded-md cursor-pointer transition-colors relative ${currentRunId === run.id ? 'bg-blue-50 border-blue-200' : 'hover:bg-gray-50'}`}
            >
              <div className="flex justify-between items-start mb-1">
                <span className="font-medium text-gray-900">{run.accession || 'Unknown Accession'}</span>
                <StatusBadge status={run.status} />
              </div>
              <p className="text-xs text-gray-500">
                {run.case_group || 'N/A'} vs {run.control_group || 'N/A'}
              </p>
              <div className="flex justify-between items-end mt-2">
                <p className="text-[10px] text-gray-400">
                  {run.created_at ? new Date(run.created_at).toLocaleString() : ''}
                </p>
                <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-2">
                  <button 
                    onClick={(e) => { e.stopPropagation(); resubmitMutation.mutate(run) }}
                    className="p-1.5 text-blue-600 hover:bg-blue-100 rounded-md transition-colors"
                    title="Resubmit Run"
                  >
                    <RotateCw className="h-3.5 w-3.5" />
                  </button>
                  <button 
                    onClick={(e) => { e.stopPropagation(); deleteMutation.mutate(run.id) }}
                    className="p-1.5 text-red-600 hover:bg-red-100 rounded-md transition-colors"
                    title="Delete Run"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
      
      <div className="col-span-8 bg-white border rounded-lg shadow-sm overflow-hidden flex flex-col">
        {currentRunId ? (
          <ErrorBoundary>
            <RunDetailView runId={currentRunId} onResubmit={(run) => resubmitMutation.mutate(run)} />
          </ErrorBoundary>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            Select a run from the left to view details
          </div>
        )}
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status?: string | null }) {
  if (!status) {
    return <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 text-xs font-medium">Unknown</span>
  }
  const norm = status.toLowerCase()
  if (norm === 'completed') {
    return <span className="px-2 py-0.5 rounded-full bg-green-100 text-green-700 text-xs font-medium flex items-center gap-1"><CheckCircle className="h-3 w-3"/> Done</span>
  }
  if (norm === 'failed') {
    return <span className="px-2 py-0.5 rounded-full bg-red-100 text-red-700 text-xs font-medium flex items-center gap-1"><XCircle className="h-3 w-3"/> Failed</span>
  }
  return <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 text-xs font-medium animate-pulse">{status.replace(/_/g, ' ')}</span>
}

interface PlotCardProps {
  title: string
  subtitle?: string
  src: string
  alt: string
  emptyMessage?: string
}

function PlotCard({ title, subtitle, src, alt, emptyMessage = 'Plot not available' }: PlotCardProps) {
  const [hasError, setHasError] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    setHasError(false)
    setIsLoading(true)
  }, [src])

  return (
    <div className="border border-gray-200 rounded-lg shadow-sm bg-white overflow-hidden flex flex-col h-[280px]">
      <div className="p-2.5 border-b bg-gray-50 flex items-center justify-between">
        <div>
          <h3 className="text-xs font-semibold text-gray-800">{title}</h3>
          {subtitle && <p className="text-[10px] text-gray-500">{subtitle}</p>}
        </div>
        {!hasError && !isLoading && (
          <span className="text-[10px] bg-green-50 text-green-700 px-1.5 py-0.5 rounded border border-green-200 font-medium">
            Ready
          </span>
        )}
      </div>

      <div className="flex-1 relative flex items-center justify-center p-2 bg-gray-50/40 overflow-hidden">
        {hasError ? (
          <div className="flex flex-col items-center justify-center text-center p-4 text-gray-400 space-y-2">
            <div className="p-2.5 bg-gray-100 rounded-full text-gray-400">
              <BarChart3 className="h-6 w-6 stroke-1" />
            </div>
            <p className="text-xs font-medium text-gray-600">{emptyMessage}</p>
            <p className="text-[10px] text-gray-400 max-w-[180px]">
              No visualization generated for this dataset or image is unavailable.
            </p>
          </div>
        ) : (
          <>
            {isLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-white/80">
                <RotateCw className="h-5 w-5 animate-spin text-blue-500" />
              </div>
            )}
            <img
              src={src}
              alt={alt}
              className={`max-w-full max-h-full object-contain transition-opacity duration-200 ${isLoading ? 'opacity-0' : 'opacity-100'}`}
              onLoad={() => setIsLoading(false)}
              onError={() => {
                setIsLoading(false)
                setHasError(true)
              }}
            />
          </>
        )}
      </div>
    </div>
  )
}

function RunDetailView({ runId, onResubmit }: { runId: string, onResubmit?: (run: any) => void }) {
  const [showPPI, setShowPPI] = useState(false)
  const fgRef = useRef<any>(null)

  const { data: run, isLoading, isError, error } = useQuery({
    queryKey: ['run', runId],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/runs/${runId}`)
      if (!res.ok) throw new Error(`HTTP error ${res.status}: Failed to fetch run details`)
      return res.json()
    },
    refetchInterval: (query: any) => {
      const status = query.state.data?.status
      return status === 'completed' || status === 'failed' ? false : 3000
    }
  })

  const { data: results, isLoading: resultsLoading } = useQuery({
    queryKey: ['results', runId],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/runs/${runId}/results`)
      if (!res.ok) throw new Error(`HTTP error ${res.status}: Failed to fetch results`)
      return res.json()
    },
    enabled: run?.status === 'completed'
  })

  useEffect(() => {
    if (showPPI && fgRef.current && results?.results?.ppi_network) {
      fgRef.current.d3Force('charge')?.strength(-200)
      fgRef.current.d3Force('link')?.distance(60)
    }
  }, [showPPI, results])

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-12 text-gray-500">
        <RotateCw className="h-8 w-8 animate-spin text-blue-600 mb-3" />
        <p className="font-medium text-sm">Loading run details...</p>
      </div>
    )
  }

  if (isError || !run) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-12 text-center">
        <div className="p-3 bg-red-100 text-red-600 rounded-full mb-3">
          <AlertCircle className="h-8 w-8" />
        </div>
        <h3 className="text-lg font-bold text-gray-800 mb-1">Failed to Load Run Details</h3>
        <p className="text-sm text-gray-600 max-w-md">
          {(error as Error)?.message || `Run "${runId}" could not be retrieved from the server.`}
        </p>
      </div>
    )
  }

  const accession = run.accession || runId
  const status = run.status || 'unknown'
  const isFailed = status === 'failed'
  const isCompleted = status === 'completed'
  const isRunning = !isFailed && !isCompleted

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* PPI Modal */}
      {showPPI && results?.results?.ppi_network && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl flex flex-col overflow-hidden">
            <div className="p-4 border-b flex justify-between items-center bg-gray-50">
              <h3 className="font-bold text-gray-800">Protein-Protein Interaction Network (STRING)</h3>
              <button 
                onClick={() => setShowPPI(false)} 
                className="text-gray-500 hover:text-gray-900 font-bold px-2 py-1 rounded transition-colors"
              >
                Close ✕
              </button>
            </div>
            <div className="w-full h-[600px]">
              <ForceGraph2D
                ref={fgRef}
                graphData={{
                  nodes: Array.from(new Set(results.results.ppi_network.flatMap((e: any) => [e.source, e.target]))).map(id => ({ id: id as string })),
                  links: results.results.ppi_network.map((e: any) => ({ source: e.source, target: e.target, value: e.score }))
                }}
                nodeLabel="id"
                nodeAutoColorBy="id"
                width={896}
                height={600}
              />
            </div>
          </div>
        </div>
      )}

      {/* Header Banner */}
      <div className="p-6 border-b bg-white flex-shrink-0">
        <div className="flex justify-between items-center mb-3">
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold text-gray-900">{accession}</h2>
            <StatusBadge status={status} />
          </div>
          {onResubmit && (
            <button
              onClick={() => onResubmit(run)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-md text-xs font-medium transition-colors"
              title="Resubmit Run"
            >
              <RotateCw className="h-3.5 w-3.5 text-blue-600" /> Resubmit Run
            </button>
          )}
        </div>
        <p className="text-sm text-gray-600">
          Comparing: <span className="font-semibold text-gray-900">{run.case_group || 'Case'}</span> vs <span className="font-semibold text-gray-900">{run.control_group || 'Control'}</span>
        </p>
      </div>

      {/* Main Body */}
      <div className="flex-1 overflow-auto p-6">
        {/* Failed Run Status Display */}
        {isFailed && (
          <div className="bg-red-50/70 border border-red-200 rounded-xl p-6 shadow-sm">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-red-100 text-red-600 rounded-xl flex-shrink-0">
                <AlertOctagon className="h-7 w-7" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between flex-wrap gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-bold text-red-900">
                      Pipeline Execution Failed: {accession}
                    </h3>
                    <StatusBadge status="failed" />
                  </div>
                  {onResubmit && (
                    <button
                      onClick={() => onResubmit(run)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-md text-xs font-semibold shadow-sm transition-colors"
                    >
                      <RotateCw className="h-3.5 w-3.5" /> Retry Run
                    </button>
                  )}
                </div>

                <p className="text-sm text-red-800 mb-4 font-medium">
                  The automated differential expression pipeline encountered an error while processing this dataset.
                </p>

                {run.error_message && (
                  <div className="bg-white border border-red-200 rounded-lg p-4 mb-4 text-xs font-mono text-red-800 break-words whitespace-pre-wrap shadow-inner">
                    <div className="text-[10px] uppercase font-bold text-red-500 mb-1 tracking-wider">Error Details</div>
                    {run.error_message}
                  </div>
                )}

                <div className="bg-white/90 border border-red-100 rounded-lg p-4 text-xs text-gray-700 space-y-2">
                  <div className="font-semibold text-gray-800 flex items-center gap-1.5 text-sm">
                    <HelpCircle className="h-4 w-4 text-amber-500" /> Troubleshooting & Guidance:
                  </div>
                  <ul className="list-disc list-inside space-y-1.5 text-gray-600 ml-1">
                    {accession.toUpperCase().startsWith('GSE') && (
                      <li>
                        <strong>Microarray vs. RNA-seq Data:</strong> If this dataset (e.g. GSE15852) represents a microarray platform (e.g. Affymetrix/Illumina), raw count matrices are not deposited in the standard RNA-seq supplement format. Microarrays require platform probe CEL file processing and probe-to-gene annotation mapping.
                      </li>
                    )}
                    <li>
                      <strong>Sample Group Labels:</strong> Ensure the specified Case (<code className="bg-gray-100 px-1 py-0.5 rounded text-gray-800">{run.case_group || 'none'}</code>) and Control (<code className="bg-gray-100 px-1 py-0.5 rounded text-gray-800">{run.control_group || 'none'}</code>) labels match valid experimental factor levels in GEO metadata.
                    </li>
                    <li>
                      <strong>GEO Server Availability:</strong> NCBI GEO FTP and HTTPS services may intermittently return 404 or rate-limit automated requests.
                    </li>
                    <li>
                      <strong>Action:</strong> Check the accession metadata on NCBI GEO, verify sample titles, or click <strong>Retry Run</strong> above to resubmit.
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Running / Pending State */}
        {isRunning && (
          <div className="flex flex-col items-center justify-center p-12 text-center bg-blue-50/40 border border-blue-100 rounded-xl">
            <div className="p-3 bg-blue-100 text-blue-600 rounded-full mb-4 animate-bounce">
              <RotateCw className="h-6 w-6 animate-spin" />
            </div>
            <h3 className="text-base font-semibold text-blue-900 mb-1">
              Pipeline Processing: {accession}
            </h3>
            <p className="text-sm text-gray-600 max-w-md mb-3">
              Differential expression analysis and multi-database biological integration are underway. Results will update automatically.
            </p>
            <span className="text-xs bg-blue-100 text-blue-700 font-medium px-3 py-1 rounded-full animate-pulse">
              Status: {status.replace(/_/g, ' ')}
            </span>
          </div>
        )}

        {/* Completed State */}
        {isCompleted && resultsLoading && (
          <div className="flex items-center justify-center p-12 text-gray-500 gap-3">
            <RotateCw className="h-5 w-5 animate-spin text-blue-600" />
            <span className="text-sm font-medium">Loading differential expression results...</span>
          </div>
        )}

        {isCompleted && !resultsLoading && results?.results && (
          <div className="space-y-8">
            {/* Global Biological Context */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-blue-900 mb-2">Master Transcription Factors (Enrichr / ChEA)</h3>
              <div className="flex flex-wrap gap-2">
                {results.results.master_tfs && results.results.master_tfs.length > 0 ? (
                  results.results.master_tfs.map((tf: string, i: number) => (
                    <span key={i} className="px-3 py-1 bg-white border border-blue-200 text-blue-700 rounded-full text-sm font-medium shadow-sm">
                      {tf}
                    </span>
                  ))
                ) : (
                  <span className="text-sm text-blue-600">No significant master TFs found.</span>
                )}
              </div>
            </div>

            {/* Plots Gallery with clean fallbacks */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 pb-6 border-b">
              <PlotCard
                title="Volcano (Significance)"
                subtitle="Significance vs. Fold Change"
                src={`${API_URL}/plots/${accession}/volcano.png`}
                alt="Volcano Plot"
                emptyMessage="Volcano plot unavailable"
              />
              <PlotCard
                title="PCA (Variance)"
                subtitle="Sample Variance Distribution"
                src={`${API_URL}/plots/${accession}/pca.png`}
                alt="PCA Plot"
                emptyMessage="PCA plot unavailable"
              />
              <PlotCard
                title="GO (Biological Process)"
                subtitle="Functional Gene Ontology"
                src={`${API_URL}/plots/${accession}/go_enrichment.png`}
                alt="GO Enrichment"
                emptyMessage="No significant GO terms detected"
              />
              <PlotCard
                title="KEGG (Pathways)"
                subtitle="Biological Pathway Enrichment"
                src={`${API_URL}/plots/${accession}/kegg_enrichment.png`}
                alt="KEGG Enrichment"
                emptyMessage="No significant KEGG pathways detected"
              />
            </div>
            
            {/* Immune Deconvolution */}
            {results.results.immune_fractions && (
              <div className="pb-6 border-b mt-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Immune Deconvolution (MCPcounter)</h3>
                <div className="h-[400px] w-full bg-white border rounded-lg shadow-sm p-4">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={Object.keys(results.results.immune_fractions).map(sample => ({
                        name: sample,
                        ...results.results.immune_fractions[sample]
                      }))}
                      margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                    >
                      <XAxis dataKey="name" />
                      <YAxis />
                      <RechartsTooltip />
                      <Legend />
                      {Object.keys(Object.values(results.results.immune_fractions)[0] || {}).map((cellType, idx) => (
                        <Bar key={idx} dataKey={cellType} stackId="a" fill={`hsl(${idx * 40}, 70%, 50%)`} />
                      ))}
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
            
            {/* Differential Expression Table Section */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-800">Top Differentially Expressed Genes</h3>
                <div className="flex gap-2">
                  {results.results.ppi_network && results.results.ppi_network.length > 0 && (
                    <button 
                      onClick={() => setShowPPI(true)} 
                      className="bg-indigo-100 text-indigo-700 px-3 py-1 rounded-md text-sm font-medium hover:bg-indigo-200 transition-colors flex items-center gap-1.5"
                    >
                      <Activity className="h-3.5 w-3.5" /> View PPI Network ({results.results.ppi_network.length})
                    </button>
                  )}
                  <div className="text-sm bg-blue-50 text-blue-700 px-3 py-1 rounded-full font-medium flex items-center">
                    {Array.isArray(results.results.results) ? results.results.results.length : 0} Genes Analyzed
                  </div>
                </div>
              </div>
              <ResultsTable data={Array.isArray(results.results.results) ? results.results.results : []} />
            </div>
          </div>
        )}

        {isCompleted && !resultsLoading && !results?.results && (
          <div className="p-8 text-center text-gray-500 bg-gray-50 rounded-xl border">
            <p className="font-medium">No differential expression results available for this run.</p>
          </div>
        )}
      </div>
    </div>
  )
}

function getGeneBiotype(symbol: string, row: any): { label: string; badgeClass: string; isUnannotated: boolean } {
  if (!symbol) {
    return { label: 'Unknown Locus', badgeClass: 'bg-gray-100 text-gray-600 border-gray-200', isUnannotated: true }
  }
  const sym = symbol.trim().toUpperCase()
  
  if (/^LOC\d+$/i.test(sym) || /^\d+$/.test(sym)) {
    return { label: 'Unannotated Locus', badgeClass: 'bg-slate-100 text-slate-700 border-slate-200', isUnannotated: true }
  }
  if (/^LINC\d+/i.test(sym) || sym.includes('-AS') || sym.endsWith('AS1')) {
    return { label: 'lncRNA', badgeClass: 'bg-indigo-50 text-indigo-700 border-indigo-200', isUnannotated: false }
  }
  if (/^MIR\d+/i.test(sym) || /^LET-7/i.test(sym)) {
    return { label: 'miRNA', badgeClass: 'bg-teal-50 text-teal-700 border-teal-200', isUnannotated: false }
  }
  if (/^SNOR/i.test(sym) || /^RNA5S/i.test(sym)) {
    return { label: 'Small RNA', badgeClass: 'bg-cyan-50 text-cyan-700 border-cyan-200', isUnannotated: false }
  }
  if (sym.startsWith('C') && sym.includes('ORF')) {
    return { label: 'Open Reading Frame', badgeClass: 'bg-amber-50 text-amber-700 border-amber-200', isUnannotated: true }
  }

  const hasProtein = Boolean(row.uniprot?.function || row.pdb?.id || row.alphafold_url)
  if (!hasProtein && !row.kegg?.pathways?.length) {
    return { label: 'Uncharacterized Gene', badgeClass: 'bg-gray-100 text-gray-600 border-gray-200', isUnannotated: true }
  }
  
  return { label: 'Protein Coding', badgeClass: 'bg-blue-50 text-blue-700 border-blue-200', isUnannotated: false }
}

function ResultsTable({ data }: { data: any[] }) {
  const [selectedStructure, setSelectedStructure] = useState<{type: 'pdb'|'url', value: string} | null>(null)

  return (
    <div className="overflow-x-auto pb-8 relative">
      {/* 3D Viewer Modal */}
      {selectedStructure && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl flex flex-col overflow-hidden">
            <div className="p-4 border-b flex justify-between items-center bg-gray-50">
              <h3 className="font-bold text-gray-800">
                3D Protein Structure ({selectedStructure.type === 'pdb' ? `PDB: ${selectedStructure.value}` : 'AlphaFold Prediction'})
              </h3>
              <button 
                onClick={() => setSelectedStructure(null)} 
                className="text-gray-500 hover:text-gray-900 font-bold px-2 py-1 rounded transition-colors"
              >
                Close ✕
              </button>
            </div>
            <div className="w-full h-[500px] bg-black">
              <iframe 
                src={`https://3dmol.csb.pitt.edu/viewer.html?${selectedStructure.type === 'pdb' ? `pdb=${selectedStructure.value}` : `url=${encodeURIComponent(selectedStructure.value)}`}&style=cartoon:color=spectrum`} 
                className="w-full h-full border-0"
                title="3D Viewer"
              ></iframe>
            </div>
          </div>
        </div>
      )}

      <table className="min-w-full text-sm text-left border-collapse bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm">
        <thead className="bg-gray-50 text-gray-700 uppercase text-[11px] font-semibold border-b tracking-wider">
          <tr>
            <th className="px-4 py-3 whitespace-nowrap">Gene</th>
            <th className="px-4 py-3 whitespace-nowrap">Base Mean</th>
            <th className="px-4 py-3 whitespace-nowrap">Log2FC</th>
            <th className="px-4 py-3 whitespace-nowrap">Adj. P-Value (padj)</th>
            <th className="px-4 py-3 whitespace-nowrap">Function</th>
            <th className="px-4 py-3 whitespace-nowrap">Pathways</th>
            <th className="px-4 py-3 whitespace-nowrap">Known Drugs (OpenTargets)</th>
            <th className="px-4 py-3 whitespace-nowrap">eQTLs (GTEx)</th>
            <th className="px-4 py-3 whitespace-nowrap">ClinVar</th>
            <th className="px-4 py-3 whitespace-nowrap text-center">Protein Structure</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {data.length === 0 ? (
            <tr>
              <td colSpan={10} className="px-4 py-8 text-center text-gray-400 italic">
                No differential expression records found.
              </td>
            </tr>
          ) : (
            data.map((row, i) => {
              const biotype = getGeneBiotype(row.symbol, row)
              const log2fcNum = row.log2fc != null && !isNaN(Number(row.log2fc)) ? Number(row.log2fc) : null
              const padjNum = row.padj != null && !isNaN(Number(row.padj)) ? Number(row.padj) : null
              const baseMeanNum = row.baseMean != null && !isNaN(Number(row.baseMean)) ? Number(row.baseMean) : null

              return (
                <tr key={i} className="hover:bg-gray-50 transition-colors">
                  {/* Gene Symbol & Tags */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="font-bold text-blue-600 text-sm">
                      {row.symbol || 'Unknown'}
                    </div>
                    <div className="flex flex-wrap gap-1 mt-1">
                      <span 
                        className={`text-[10px] px-1.5 py-0.5 rounded border font-medium ${biotype.badgeClass}`}
                        title={`Biotype: ${biotype.label}`}
                      >
                        {biotype.label}
                      </span>
                      {row.depmap_essential && (
                        <span className="text-[10px] bg-red-100 text-red-800 px-1.5 py-0.5 rounded border border-red-200 font-bold" title="DepMap CRISPR Essential Gene">
                          🔥 ESSENTIAL
                        </span>
                      )}
                      {row.tcga_survival && (
                        <span className="text-[10px] bg-yellow-100 text-yellow-800 px-1.5 py-0.5 rounded border border-yellow-200 font-bold" title="Cancer Prognostic Marker (TCGA)">
                          🎗️ CANCER PROGNOSTIC
                        </span>
                      )}
                    </div>
                  </td>

                  {/* baseMean */}
                  <td className="px-4 py-3 whitespace-nowrap font-mono text-xs text-gray-700">
                    {baseMeanNum != null ? baseMeanNum.toLocaleString(undefined, { maximumFractionDigits: 1 }) : (
                      <span className="text-gray-400 italic">N/A</span>
                    )}
                  </td>

                  {/* Log2FC */}
                  <td className="px-4 py-3 whitespace-nowrap font-mono text-xs">
                    {log2fcNum != null ? (
                      <span className={log2fcNum > 0 ? "text-red-600 font-semibold" : "text-blue-600 font-semibold"}>
                        {log2fcNum > 0 ? `+${log2fcNum.toFixed(2)}` : log2fcNum.toFixed(2)}
                      </span>
                    ) : (
                      <span className="text-gray-400 italic">N/A</span>
                    )}
                  </td>

                  {/* padj */}
                  <td className="px-4 py-3 whitespace-nowrap font-mono text-xs">
                    {padjNum != null ? (
                      <span 
                        className={padjNum < 0.05 ? "font-bold text-gray-900 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200" : "text-gray-600"}
                        title={`padj = ${padjNum}`}
                      >
                        {padjNum < 0.001 ? padjNum.toExponential(3) : padjNum.toFixed(4)}
                      </span>
                    ) : (
                      <span className="text-gray-400 italic">N/A</span>
                    )}
                  </td>
                  
                  {/* Function */}
                  <td className="px-4 py-3 min-w-[200px] max-w-[300px]">
                    {row.uniprot?.function ? (
                      <>
                        <div className="line-clamp-2 text-xs text-gray-800" title={row.uniprot.function}>
                          {row.uniprot.function}
                        </div>
                        {row.uniprot?.source_url && (
                          <a href={row.uniprot.source_url} target="_blank" rel="noreferrer" className="text-[11px] text-blue-500 hover:underline inline-flex items-center mt-1">
                            UniProt ↗
                          </a>
                        )}
                      </>
                    ) : biotype.isUnannotated ? (
                      <span className="text-xs text-gray-400 italic">Unannotated / non-protein locus</span>
                    ) : (
                      <span className="text-xs text-gray-400 italic">No UniProt record</span>
                    )}
                  </td>
                  
                  {/* Pathways */}
                  <td className="px-4 py-3 min-w-[160px] max-w-[240px]">
                    {row.kegg?.pathways && row.kegg.pathways.length > 0 ? (
                      <>
                        <div className="line-clamp-2 text-xs text-gray-800" title={row.kegg.pathways.join(", ")}>
                          {row.kegg.pathways.join(", ")}
                        </div>
                        {row.kegg?.source_url && (
                          <a href={row.kegg.source_url} target="_blank" rel="noreferrer" className="text-[11px] text-green-600 hover:underline inline-flex items-center mt-1">
                            KEGG ↗
                          </a>
                        )}
                      </>
                    ) : biotype.isUnannotated ? (
                      <span className="text-xs text-gray-400 italic">No KEGG annotation</span>
                    ) : (
                      <span className="text-xs text-gray-400 italic">None mapped</span>
                    )}
                  </td>
                  
                  {/* Known Drugs */}
                  <td className="px-4 py-3 min-w-[150px]">
                    {row.drugs && row.drugs.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {row.drugs.map((d: string, j: number) => (
                          <span key={j} className="text-[10px] bg-purple-100 text-purple-800 px-2 py-0.5 rounded border border-purple-200">
                            {d}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-gray-400 text-xs italic">None known</span>
                    )}
                  </td>

                  {/* eQTLs */}
                  <td className="px-4 py-3 min-w-[150px]">
                    {row.eqtl && row.eqtl.length > 0 ? (
                      <div className="flex flex-col gap-1">
                        {row.eqtl.map((q: any, j: number) => (
                          <span key={j} className="text-[10px] text-gray-600 font-mono">
                            {q.tissueSiteDetailId}: {q.variantId}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-gray-400 text-xs italic">None reported</span>
                    )}
                  </td>

                  {/* ClinVar */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div>
                      <span className="text-xs text-gray-800 font-medium">
                        {row.clinvar?.status || 'No variants'}
                      </span>
                    </div>
                    {row.clinvar?.source_url && (
                      <a href={row.clinvar.source_url} target="_blank" rel="noreferrer" className="text-[11px] text-purple-500 hover:underline inline-flex items-center mt-1">
                        ClinVar ↗
                      </a>
                    )}
                  </td>

                  {/* Protein Structure */}
                  <td className="px-4 py-3 whitespace-nowrap text-center">
                    {row.pdb?.id ? (
                      <button 
                        onClick={() => setSelectedStructure({type: 'pdb', value: row.pdb.id})}
                        className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1.5 rounded-md font-medium shadow-sm flex items-center gap-1 transition-colors w-full justify-center"
                      >
                        <Activity className="h-3 w-3" /> PDB: {row.pdb.id}
                      </button>
                    ) : row.alphafold_url ? (
                      <button 
                        onClick={() => setSelectedStructure({type: 'url', value: row.alphafold_url})}
                        className="text-xs bg-cyan-600 hover:bg-cyan-700 text-white px-3 py-1.5 rounded-md font-medium shadow-sm flex items-center gap-1 transition-colors w-full justify-center"
                      >
                        <Activity className="h-3 w-3" /> AlphaFold 3D
                      </button>
                    ) : biotype.isUnannotated ? (
                      <span className="text-gray-400 text-xs italic">Non-coding / No Structure</span>
                    ) : (
                      <span className="text-gray-400 text-xs italic">No Structure</span>
                    )}
                  </td>
                </tr>
              )
            })
          )}
        </tbody>
      </table>
    </div>
  )
}

export default App
