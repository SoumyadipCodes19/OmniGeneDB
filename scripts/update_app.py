import os
import re

app_file = r"C:\Users\soumy\Downloads\OmniGeneDB\frontend\src\App.tsx"

with open(app_file, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add imports
content = content.replace(
    "import { Activity, Play, List, CheckCircle, XCircle, Trash2, RotateCw } from 'lucide-react'",
    "import { Activity, Play, List, CheckCircle, XCircle, Trash2, RotateCw } from 'lucide-react'\nimport ForceGraph2D from 'react-force-graph-2d'\nimport { BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip, Legend, ResponsiveContainer } from 'recharts'"
)

# 2. Add isCancer state in SubmitRunView
content = content.replace(
    "const [topN, setTopN] = useState(50)",
    "const [topN, setTopN] = useState(50)\n  const [isCancer, setIsCancer] = useState(false)"
)

content = content.replace(
    "className=\"w-full p-2 border rounded-md\"\n            value={topN}\n            onChange={e => setTopN(parseInt(e.target.value) || 50)}\n          />\n          <p className=\"text-xs text-gray-500 mt-1\">Note: High numbers will take longer to fetch from external databases.</p>\n        </div>",
    "className=\"w-full p-2 border rounded-md\"\n            value={topN}\n            onChange={e => setTopN(parseInt(e.target.value) || 50)}\n          />\n          <p className=\"text-xs text-gray-500 mt-1\">Note: High numbers will take longer to fetch from external databases.</p>\n        </div>\n\n        <div>\n          <label className=\"flex items-center space-x-2 text-sm font-medium text-gray-700 mb-4 cursor-pointer\">\n            <input type=\"checkbox\" className=\"rounded text-blue-600 border-gray-300 focus:ring-blue-500\" checked={isCancer} onChange={e => setIsCancer(e.target.checked)} />\n            <span>Is this a Cancer dataset? (Enables TCGA Survival Analysis)</span>\n          </label>\n        </div>"
)

content = content.replace(
    "mutation.mutate({ accession, case_group: caseGroup, control_group: controlGroup, top_n: topN })",
    "mutation.mutate({ accession, case_group: caseGroup, control_group: controlGroup, top_n: topN, is_cancer: isCancer })"
)

# 3. Add showPPI state and modal in RunDetailView
content = content.replace(
    "function RunDetailView({ runId }: { runId: string }) {",
    "function RunDetailView({ runId }: { runId: string }) {\n  const [showPPI, setShowPPI] = useState(false)"
)

# Add View PPI button
content = content.replace(
    """            <div className="flex items-center justify-between mb-4">
               <h3 className="text-lg font-semibold text-gray-800">Top Differentially Expressed Genes</h3>
               <div className="text-sm bg-blue-50 text-blue-700 px-3 py-1 rounded-full font-medium">
                  {results.results.results?.length || 0} Genes Analyzed
               </div>
            </div>""",
    """            <div className="flex items-center justify-between mb-4">
               <h3 className="text-lg font-semibold text-gray-800">Top Differentially Expressed Genes</h3>
               <div className="flex gap-2">
                 <button onClick={() => setShowPPI(true)} className="bg-indigo-100 text-indigo-700 px-3 py-1 rounded-md text-sm font-medium hover:bg-indigo-200 transition-colors">
                   View PPI Network
                 </button>
                 <div className="text-sm bg-blue-50 text-blue-700 px-3 py-1 rounded-full font-medium flex items-center">
                    {results.results.results?.length || 0} Genes Analyzed
                 </div>
               </div>
            </div>"""
)

# Add Modal
modal_code = """
      {showPPI && results?.results?.ppi_network && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl flex flex-col overflow-hidden">
            <div className="p-4 border-b flex justify-between items-center bg-gray-50">
              <h3 className="font-bold text-gray-800">Protein-Protein Interaction Network (STRING)</h3>
              <button onClick={() => setShowPPI(false)} className="text-gray-500 hover:text-gray-900 font-bold px-2">Close ✕</button>
            </div>
            <div className="w-full h-[600px]">
              <ForceGraph2D
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
"""

content = content.replace(
    "return (\n    <div className=\"flex flex-col h-full\">",
    f"return (\n    <div className=\"flex flex-col h-full\">\n{modal_code}"
)

# 4. Remove Immune Infiltration PNG and add Recharts
# Remove PNG:
png_block = """              <div className="border rounded-lg shadow-sm bg-white overflow-hidden p-2">
                <h3 className="text-center text-xs font-semibold text-gray-700 mb-2">Immune Deconvolution</h3>
                <img src={`${API_URL}/plots/${run.accession}/immune_infiltration.png`} alt="Immune Cells" className="w-full h-auto object-cover" 
                     onError={(e) => e.currentTarget.style.display = 'none'} />
              </div>"""

content = content.replace(png_block, "")

# Make the grid 4 columns
content = content.replace("grid-cols-2 lg:grid-cols-5 gap-4", "grid-cols-2 lg:grid-cols-4 gap-4")

recharts_block = """            
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
"""

content = content.replace(
    "</div>\n            \n            <div className=\"flex items-center justify-between mb-4\">",
    "</div>\n" + recharts_block + "            \n            <div className=\"flex items-center justify-between mb-4\">"
)

# 5. Table upgrades
content = content.replace(
    "<th className=\"px-4 py-3 whitespace-nowrap\">Known Drugs (OpenTargets)</th>\n            <th className=\"px-4 py-3 whitespace-nowrap\">ClinVar</th>",
    "<th className=\"px-4 py-3 whitespace-nowrap\">Known Drugs (OpenTargets)</th>\n            <th className=\"px-4 py-3 whitespace-nowrap\">eQTLs (GTEx)</th>\n            <th className=\"px-4 py-3 whitespace-nowrap\">ClinVar</th>"
)

badge_code = """                {row.tcga_survival && (
                  <div className="mt-1">
                    <span className="text-[10px] bg-yellow-100 text-yellow-800 px-1.5 py-0.5 rounded border border-yellow-200 font-bold" title="Cancer Prognostic Marker (TCGA)">
                      🎗️ CANCER PROGNOSTIC
                    </span>
                  </div>
                )}"""

content = content.replace(
    "🔥 ESSENTIAL\n                    </span>\n                  </div>\n                )}",
    "🔥 ESSENTIAL\n                    </span>\n                  </div>\n                )}\n" + badge_code
)

eqtl_col = """              <td className="px-4 py-3 min-w-[150px]">
                {row.eqtl && row.eqtl.length > 0 ? (
                  <div className="flex flex-col gap-1">
                    {row.eqtl.map((q: any, j: number) => (
                      <span key={j} className="text-[10px] text-gray-600">
                        {q.tissueSiteDetailId}: {q.variantId}
                      </span>
                    ))}
                  </div>
                ) : (
                  <span className="text-gray-400 italic">None</span>
                )}
              </td>"""

content = content.replace(
    "</span>\n                )}\n              </td>\n              \n              <td className=\"px-4 py-3 whitespace-nowrap\">",
    "</span>\n                )}\n              </td>\n" + eqtl_col + "\n              <td className=\"px-4 py-3 whitespace-nowrap\">"
)


with open(app_file, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated App.tsx successfully.")
