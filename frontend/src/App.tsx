import { useState, useRef } from "react";

type Phase = "idle" | "running" | "complete" | "error";
type SourceTab = "git" | "local" | "zip";

// ── Call graph types ───────────────────────────────────────────────────────────
interface GraphNode { id: string; group: "a" | "b" | "shared"; }
interface GraphEdge { source: string; target: string; repo: "a" | "b" | "shared"; }
interface GraphData { nodes: GraphNode[]; edges: GraphEdge[]; }

interface MatchingBlock {
  a_line_start: number;
  b_line_start: number;
  length: number;
  lines: string[];
}

interface FileMatchDetail {
  line_ratio?: number;
  matching_blocks?: MatchingBlock[];
  shared_functions?: string[];
  ast_jaccard?: number;
  hash?: string;
  [key: string]: unknown;
}

interface FileMatch {
  file_a_path: string;
  file_b_path: string;
  similarity_score: number;
  method_id: string;
  detail: FileMatchDetail;
}

interface MethodResult {
  method_id: string;
  score: number;
  weight: number;
  duration_ms: number;
  details: Record<string, unknown>;
}

interface CompareResult {
  job_id: string;
  repo_a_name: string;
  repo_b_name: string;
  language: string;
  files_found_a: number;
  files_found_b: number;
  overall_score: number;
  methods: MethodResult[];
  file_matches: FileMatch[];
  output_file: string;
  created_at: string;
}

const METHOD_NAMES: Record<string, string> = {
  file_hash: "Exact File Hash",
  line_similarity: "Line Similarity",
  function_names: "Function Names",
  ast_structure: "AST Structure",
  token_ngram: "Token N-gram",
  call_graph: "Call Graph",
  import_analysis: "Import Analysis",
  identifier_similarity: "Identifier Names",
  complexity_profile: "Complexity Profile",
};

const METHOD_DESC: Record<string, string> = {
  file_hash: "Files with identical content after stripping comments and whitespace",
  line_similarity: "Fraction of lines in Repo B that appear in Repo A",
  function_names: "Jaccard overlap of function/class/method names",
  ast_structure: "Structural shape of the AST ignoring variable names",
  token_ngram: "Winnowing fingerprint overlap (MOSS-style)",
  call_graph: "Similarity of function call topology",
  import_analysis: "Overlap of imported packages and modules",
  identifier_similarity: "Overlap of variable and identifier names",
  complexity_profile: "Cosine similarity of cyclomatic complexity histograms",
};

const DETAIL_LABELS: Record<string, string> = {
  matched_files: "Identical files",
  total_b_files: "Files in B",
  avg_best_ratio: "Avg line match",
  shared_count: "Shared count",
  unique_to_a: "Only in A",
  unique_to_b: "Only in B",
  avg_ast_jaccard: "Avg AST Jaccard",
  avg_ngram_jaccard: "Avg N-gram Jaccard",
  k: "K-gram length",
  w: "Window size",
  avg_call_graph_sim: "Avg graph similarity",
  complexity_cosine: "Cosine similarity",
  a_func_count: "Functions in A",
  b_func_count: "Functions in B",
};

const ARRAY_DETAIL_KEYS = new Set(["shared_names", "shared_imports", "shared_identifiers"]);

function scoreColor(s: number) {
  return s >= 0.7 ? "text-red-600" : s >= 0.4 ? "text-yellow-500" : "text-green-600";
}
function scoreBg(s: number) {
  return s >= 0.7 ? "bg-red-50 border-red-200" : s >= 0.4 ? "bg-yellow-50 border-yellow-200" : "bg-green-50 border-green-200";
}
function scoreBar(s: number) {
  return s >= 0.7 ? "bg-red-400" : s >= 0.4 ? "bg-yellow-400" : "bg-green-400";
}

function Pct({ score }: { score: number }) {
  return <span className={`font-semibold tabular-nums ${scoreColor(score)}`}>{(score * 100).toFixed(1)}%</span>;
}

function MiniBar({ score }: { score: number }) {
  return (
    <div className="flex items-center gap-2 shrink-0">
      <div className="w-24 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${scoreBar(score)}`} style={{ width: `${score * 100}%` }} />
      </div>
      <Pct score={score} />
    </div>
  );
}

// ── Repo input card ────────────────────────────────────────────────────────────

interface RepoCardProps {
  label: string;
  accent: string;
  name: string; onNameChange: (v: string) => void;
  tab: SourceTab; onTabChange: (t: SourceTab) => void;
  url: string; onUrlChange: (v: string) => void;
  path: string; onPathChange: (v: string) => void;
  file: File | null; onFileChange: (f: File | null) => void;
}

function RepoCard({ label, accent, name, onNameChange, tab, onTabChange, url, onUrlChange, path, onPathChange, file, onFileChange }: RepoCardProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const dirRef = useRef<HTMLInputElement>(null);
  const tabs: { id: SourceTab; label: string }[] = [
    { id: "git", label: "Git URL" },
    { id: "local", label: "Local Path" },
    { id: "zip", label: "Upload ZIP" },
  ];

  const handleDirSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    // webkitRelativePath is "foldername/subdir/file.txt" — extract the top-level folder name
    const rel: string = (files[0] as File & { webkitRelativePath?: string }).webkitRelativePath ?? "";
    const folderName = rel.split("/")[0] || files[0].name;
    onPathChange(folderName);
    e.target.value = "";
  };

  return (
    <div className={`border-2 ${accent} rounded-xl p-5 flex flex-col gap-4`}>
      <h3 className="font-semibold text-gray-700 text-sm uppercase tracking-wide">{label}</h3>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Name</label>
        <input type="text" value={name} onChange={e => onNameChange(e.target.value)} placeholder="e.g. project-alpha"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
      </div>
      <div className="flex gap-1 border border-gray-200 rounded-lg p-1 bg-gray-50">
        {tabs.map(t => (
          <button key={t.id} type="button" onClick={() => onTabChange(t.id)}
            className={`flex-1 text-xs py-1.5 rounded-md font-medium transition-colors ${tab === t.id ? "bg-white shadow text-blue-600" : "text-gray-500 hover:text-gray-700"}`}>
            {t.label}
          </button>
        ))}
      </div>
      {tab === "git" && (
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Git URL</label>
          <input type="text" value={url} onChange={e => onUrlChange(e.target.value)} placeholder="https://github.com/org/repo.git"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        </div>
      )}
      {tab === "local" && (
        <div className="flex flex-col gap-1.5">
          <label className="block text-xs font-medium text-gray-600">Local Path</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={path}
              onChange={e => onPathChange(e.target.value)}
              placeholder="/path/to/repo"
              className="flex-1 min-w-0 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
            <button
              type="button"
              onClick={() => dirRef.current?.click()}
              className="shrink-0 border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 hover:border-gray-400 transition-colors"
            >
              Browse…
            </button>
          </div>
          <p className="text-xs text-gray-400">
            Browse fills in the folder name — prepend the full path if needed.
          </p>
          {/* Hidden directory picker — webkitdirectory is non-standard but widely supported */}
          <input
            ref={dirRef}
            type="file"
            className="hidden"
            onChange={handleDirSelect}
            {...{ webkitdirectory: "" } as React.InputHTMLAttributes<HTMLInputElement>}
          />
        </div>
      )}
      {tab === "zip" && (
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">ZIP File</label>
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center cursor-pointer hover:border-blue-400 transition-colors" onClick={() => fileRef.current?.click()}>
            {file ? (
              <p className="text-sm text-gray-700"><span className="font-medium">{file.name}</span> <span className="text-gray-400">({(file.size / 1024).toFixed(0)} KB)</span></p>
            ) : (
              <p className="text-sm text-gray-400">Click to select a .zip file</p>
            )}
          </div>
          <input ref={fileRef} type="file" accept=".zip" className="hidden" onChange={e => onFileChange(e.target.files?.[0] ?? null)} />
        </div>
      )}
    </div>
  );
}

// ── Call graph visualization ───────────────────────────────────────────────────

const NODE_COLORS: Record<string, string> = { a: "#3b82f6", shared: "#8b5cf6", b: "#f97316" };
const EDGE_COLORS: Record<string, string> = { a: "#bfdbfe", shared: "#ddd6fe", b: "#fed7aa" };

function CallGraphViz({ graph, nameA, nameB }: { graph: GraphData; nameA: string; nameB: string }) {
  const R = 5;
  const LABEL_MAX = 20;
  const ROW_H = 22;
  const SVG_W = 900;
  const PAD_TOP = 36;
  const PAD_BOT = 24;

  const aNodes = graph.nodes.filter(n => n.group === "a");
  const sNodes = graph.nodes.filter(n => n.group === "shared");
  const bNodes = graph.nodes.filter(n => n.group === "b");

  const maxRows = Math.max(aNodes.length, sNodes.length, bNodes.length, 1);
  const SVG_H = PAD_TOP + PAD_BOT + maxRows * ROW_H;

  // Column x positions
  const CX = { a: 200, shared: 450, b: 700 };

  const pos: Record<string, { x: number; y: number }> = {};

  function placeCol(nodes: GraphNode[], x: number) {
    const span = (nodes.length - 1) * ROW_H;
    const startY = PAD_TOP + (SVG_H - PAD_TOP - PAD_BOT - span) / 2;
    nodes.forEach((n, i) => { pos[n.id] = { x, y: startY + i * ROW_H }; });
  }
  placeCol(aNodes, CX.a);
  placeCol(sNodes, CX.shared);
  placeCol(bNodes, CX.b);

  const trunc = (s: string) => s.length > LABEL_MAX ? s.slice(0, LABEL_MAX - 1) + "…" : s;

  function renderEdge(e: GraphEdge, i: number) {
    const s = pos[e.source], t = pos[e.target];
    if (!s || !t) return null;
    const dx = t.x - s.x, dy = t.y - s.y;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
    // Pull endpoints to circle surface
    const x1 = s.x + (dx / dist) * (R + 1);
    const y1 = s.y + (dy / dist) * (R + 1);
    const x2 = t.x - (dx / dist) * (R + 4);
    const y2 = t.y - (dy / dist) * (R + 4);
    const color = EDGE_COLORS[e.repo];
    // Same column → curved arc to avoid overlapping nodes
    if (Math.abs(s.x - t.x) < 5) {
      const bend = s.x < SVG_W / 2 ? -55 : 55;
      return (
        <path key={i} d={`M${x1},${y1} Q${s.x + bend},${(s.y + t.y) / 2} ${x2},${y2}`}
          fill="none" stroke={color} strokeWidth={1} strokeOpacity={0.75}
          markerEnd={`url(#arr-${e.repo})`} />
      );
    }
    return (
      <line key={i} x1={x1} y1={y1} x2={x2} y2={y2}
        stroke={color} strokeWidth={1} strokeOpacity={0.6}
        markerEnd={`url(#arr-${e.repo})`} />
    );
  }

  const truncName = (s: string) => s.length > 14 ? s.slice(0, 5) + "…" : s;

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white p-2">
      <svg width={SVG_W} height={SVG_H} style={{ fontFamily: "ui-monospace, monospace", display: "block" }}>
        <defs>
          {(["a", "b", "shared"] as const).map(repo => (
            <marker key={repo} id={`arr-${repo}`} markerWidth={5} markerHeight={5} refX={4} refY={2.5} orient="auto">
              <path d="M0,0 L0,5 L5,2.5 z" fill={EDGE_COLORS[repo]} />
            </marker>
          ))}
        </defs>

        {/* Dashed column dividers */}
        <line x1={325} y1={28} x2={325} y2={SVG_H - 8} stroke="#e5e7eb" strokeWidth={1} strokeDasharray="4,3" />
        <line x1={575} y1={28} x2={575} y2={SVG_H - 8} stroke="#e5e7eb" strokeWidth={1} strokeDasharray="4,3" />

        {/* Column headers */}
        <text x={CX.a} y={18} textAnchor="middle" fontSize={11} fontWeight="600" fill="#2563eb">
          {truncName(nameA)} only ({aNodes.length})
        </text>
        <text x={CX.shared} y={18} textAnchor="middle" fontSize={11} fontWeight="600" fill="#7c3aed">
          Shared ({sNodes.length})
        </text>
        <text x={CX.b} y={18} textAnchor="middle" fontSize={11} fontWeight="600" fill="#ea580c">
          {truncName(nameB)} only ({bNodes.length})
        </text>

        {/* Edges first so nodes render on top */}
        {graph.edges.map((e, i) => renderEdge(e, i))}

        {/* Nodes + labels */}
        {graph.nodes.map(n => {
          const p = pos[n.id];
          if (!p) return null;
          // A-only: label to the left; shared + B: label to the right
          const labelLeft = n.group === "a";
          return (
            <g key={n.id}>
              <title>{n.id}</title>
              <circle cx={p.x} cy={p.y} r={R} fill={NODE_COLORS[n.group]} />
              <text
                x={labelLeft ? p.x - R - 4 : p.x + R + 4}
                y={p.y + 3}
                textAnchor={labelLeft ? "end" : "start"}
                fontSize={9}
                fill="#374151"
              >
                {trunc(n.id)}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 px-2 pt-1 pb-0.5 text-xs text-gray-500">
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: NODE_COLORS.a }} />
          {nameA} only
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: NODE_COLORS.shared }} />
          Shared
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: NODE_COLORS.b }} />
          {nameB} only
        </span>
        <span className="text-gray-400">Arrows show function calls. Hover a node for its full name.</span>
      </div>
    </div>
  );
}

// ── Shared pills ───────────────────────────────────────────────────────────────

function SharedPills({ label, items, colorClass }: { label: string; items: string[]; colorClass: string }) {
  const [showAll, setShowAll] = useState(false);
  const limit = 24;
  const visible = showAll ? items : items.slice(0, limit);
  return (
    <div>
      <p className="text-xs font-semibold text-gray-500 mb-1.5">{label}</p>
      <div className="flex flex-wrap gap-1">
        {visible.map(n => (
          <code key={n} className={`text-xs rounded px-1.5 py-0.5 ${colorClass}`}>{n}</code>
        ))}
        {!showAll && items.length > limit && (
          <button type="button" onClick={() => setShowAll(true)}
            className="text-xs text-blue-500 hover:underline px-1.5 py-0.5">
            +{items.length - limit} more
          </button>
        )}
      </div>
    </div>
  );
}

// ── File pair detail ──────────────────────────────────────────────────────────

function FilePairDetail({ fm }: { fm: FileMatch }) {
  const [open, setOpen] = useState(false);
  const blocks = fm.detail?.matching_blocks ?? [];
  const sharedFns = fm.detail?.shared_functions ?? [];
  const hasExpandable = blocks.length > 0 || sharedFns.length > 0 ||
    (blocks.length === 0 && sharedFns.length === 0 && Object.keys(fm.detail ?? {}).length > 0);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="flex items-center gap-2 bg-white px-3 py-2 text-xs">
        <div className="flex items-center gap-1.5 min-w-0 flex-1">
          <code className="text-blue-700 truncate max-w-[180px]">{fm.file_a_path}</code>
          <span className="text-gray-400 shrink-0">↔</span>
          <code className="text-orange-700 truncate max-w-[180px]">{fm.file_b_path}</code>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Pct score={fm.similarity_score} />
          {hasExpandable && (
            <button type="button" onClick={() => setOpen(o => !o)}
              className="text-gray-400 hover:text-gray-600 transition-colors flex items-center gap-0.5">
              <span className={`transition-transform duration-150 inline-block ${open ? "rotate-90" : ""}`}>▶</span>
              <span className="ml-0.5">{open ? "hide" : "code"}</span>
            </button>
          )}
        </div>
      </div>

      {open && (
        <>
          {sharedFns.length > 0 && (
            <div className="px-3 py-2 border-t border-gray-100 bg-orange-50/30">
              <p className="text-xs text-gray-500 mb-1">Shared functions in this pair:</p>
              <div className="flex flex-wrap gap-1">
                {sharedFns.map(fn => (
                  <code key={fn} className="text-xs bg-orange-50 text-orange-700 border border-orange-200 rounded px-1.5 py-0.5">{fn}</code>
                ))}
              </div>
            </div>
          )}

          {blocks.length > 0 && (
            <div className="divide-y divide-gray-100">
              {blocks.map((b, i) => (
                <div key={i} className="px-3 py-2">
                  <div className="flex gap-4 text-xs text-gray-400 mb-1.5">
                    <span className="text-blue-600">A:{b.a_line_start}–{b.a_line_start + b.length - 1}</span>
                    <span className="text-orange-600">B:{b.b_line_start}–{b.b_line_start + b.length - 1}</span>
                    <span className="text-gray-400">{b.length} lines</span>
                  </div>
                  <pre className="text-xs bg-gray-900 text-green-400 rounded-md p-2.5 overflow-x-auto max-h-40 leading-relaxed">{b.lines.join("\n")}</pre>
                </div>
              ))}
            </div>
          )}

          {blocks.length === 0 && sharedFns.length === 0 && Object.keys(fm.detail ?? {}).length > 0 && (
            <div className="px-3 py-2 border-t border-gray-100">
              <pre className="text-xs text-gray-500 whitespace-pre-wrap">{JSON.stringify(fm.detail, null, 2)}</pre>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── Method card (collapsible) ──────────────────────────────────────────────────

function MethodCard({ method, matches, nameA, nameB }: { method: MethodResult; matches: FileMatch[]; nameA: string; nameB: string }) {
  const [open, setOpen] = useState(false);
  const d = method.details;

  const sharedNames = (d.shared_names as string[] | undefined) ?? [];
  const sharedImports = (d.shared_imports as string[] | undefined) ?? [];
  const sharedIds = (d.shared_identifiers as string[] | undefined) ?? [];

  const stats = Object.entries(d)
    .filter(([k, v]) => !ARRAY_DETAIL_KEYS.has(k) && k !== "error" && DETAIL_LABELS[k] != null && v != null)
    .map(([k, v]) => ({ label: DETAIL_LABELS[k], raw: k, value: String(v) }));

  const hasError = d.error != null;
  const graphData = method.method_id === "call_graph" ? (d.graph as GraphData | undefined) : undefined;
  const hasGraph = (graphData?.nodes.length ?? 0) > 0;

  const hasContent =
    stats.length > 0 ||
    sharedNames.length > 0 ||
    sharedImports.length > 0 ||
    sharedIds.length > 0 ||
    matches.length > 0 ||
    hasError ||
    hasGraph;

  return (
    <div>
      <button
        type="button"
        onClick={() => hasContent && setOpen(o => !o)}
        className={`w-full text-left px-5 py-3 flex items-center gap-3 transition-colors ${hasContent ? "hover:bg-gray-50 cursor-pointer" : "cursor-default"}`}
      >
        <span className={`text-xs transition-transform duration-150 inline-block shrink-0 ${open ? "rotate-90" : ""} ${hasContent ? "text-gray-400" : "text-transparent"}`}>
          ▶
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-gray-800 text-sm">{METHOD_NAMES[method.method_id] ?? method.method_id}</span>
            <span className="text-xs text-gray-400">{(method.weight * 100).toFixed(0)}% weight</span>
            <span className="text-xs text-gray-300">{method.duration_ms}ms</span>
            {matches.length > 0 && (
              <span className="text-xs bg-gray-100 text-gray-500 rounded px-1.5 py-0.5">
                {matches.length} file pair{matches.length !== 1 ? "s" : ""}
              </span>
            )}
            {hasError && <span className="text-xs text-red-500 font-medium">⚠ error</span>}
          </div>
          <p className="text-xs text-gray-400 mt-0.5">{METHOD_DESC[method.method_id]}</p>
        </div>
        <MiniBar score={method.score} />
      </button>

      {open && hasContent && (
        <div className="border-t border-gray-100 bg-gray-50/50 px-5 py-4 space-y-4">

          {/* Score breakdown stats */}
          {stats.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Score breakdown</p>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {stats.map(({ label, raw, value }) => {
                  const isRatio = raw.includes("ratio") || raw.includes("jaccard") || raw.includes("cosine") || raw.includes("sim");
                  const display = isRatio ? `${(parseFloat(value) * 100).toFixed(1)}%` : value;
                  return (
                    <div key={raw} className="bg-white border border-gray-200 rounded-lg px-3 py-2.5">
                      <div className="text-xs text-gray-400 mb-0.5">{label}</div>
                      <div className="text-sm font-semibold text-gray-800">{display}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Call graph visualization */}
          {hasGraph && graphData && (
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Call Graph</p>
              <CallGraphViz graph={graphData} nameA={nameA} nameB={nameB} />
            </div>
          )}

          {/* Error */}
          {hasError && (
            <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">
              <span className="font-semibold">Error: </span>{String(d.error)}
            </div>
          )}

          {/* Shared symbols */}
          {sharedNames.length > 0 && (
            <SharedPills
              label={`Shared function / class names — ${sharedNames.length} total`}
              items={sharedNames}
              colorClass="bg-orange-50 text-orange-700 border border-orange-200"
            />
          )}
          {sharedImports.length > 0 && (
            <SharedPills
              label={`Shared imports — ${sharedImports.length} total`}
              items={sharedImports}
              colorClass="bg-purple-50 text-purple-700 border border-purple-200"
            />
          )}
          {sharedIds.length > 0 && (
            <SharedPills
              label={`Shared identifiers — ${sharedIds.length} total`}
              items={sharedIds}
              colorClass="bg-blue-50 text-blue-700 border border-blue-200"
            />
          )}

          {/* File pair matches */}
          {matches.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
                File pairs ({matches.length})
              </p>
              {matches.map((fm, i) => (
                <FilePairDetail key={i} fm={fm} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Results view ──────────────────────────────────────────────────────────────

function ResultsView({ result, onReset }: { result: CompareResult; onReset: () => void }) {
  const matchesByMethod: Record<string, FileMatch[]> = {};
  for (const fm of result.file_matches) {
    (matchesByMethod[fm.method_id] ??= []).push(fm);
  }

  const handleDownload = () => {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `comparison_${result.job_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const noFiles = result.files_found_a === 0 || result.files_found_b === 0;

  return (
    <div className="space-y-6">
      {/* Score card */}
      <div className={`border-2 rounded-xl p-8 text-center ${scoreBg(result.overall_score)}`}>
        <div className={`text-6xl font-bold ${scoreColor(result.overall_score)}`}>
          {(result.overall_score * 100).toFixed(1)}%
        </div>
        <div className="text-lg font-semibold text-gray-700 mt-2">Similarity Score</div>
        <div className="text-sm text-gray-500 mt-1">{result.repo_a_name} vs {result.repo_b_name}</div>
        <div className="flex gap-4 justify-center mt-3 text-xs text-gray-500">
          <span>{result.files_found_a} {result.language} files in A</span>
          <span>·</span>
          <span>{result.files_found_b} {result.language} files in B</span>
        </div>
        {noFiles && (
          <div className="mt-3 mx-auto max-w-sm bg-yellow-100 border border-yellow-300 text-yellow-800 text-sm rounded-lg px-4 py-2">
            No supported source files found — repos must contain .py, .js, .ts, .jsx, or .tsx files.
          </div>
        )}
        <div className="flex gap-3 justify-center mt-5">
          <button onClick={handleDownload} className="bg-white border border-gray-300 hover:border-gray-400 text-gray-700 text-sm font-medium px-4 py-2 rounded-lg transition-colors">
            Download JSON
          </button>
          <button onClick={onReset} className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors">
            New Comparison
          </button>
        </div>
      </div>

      {/* Method breakdown */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-100">
          <h2 className="font-semibold text-gray-800">Method Breakdown</h2>
          <p className="text-xs text-gray-400 mt-0.5">Click any method row to expand score details, matched files, and code sections</p>
        </div>
        <div className="divide-y divide-gray-100">
          {result.methods.map(m => (
            <MethodCard
              key={m.method_id}
              method={m}
              matches={matchesByMethod[m.method_id] ?? []}
              nameA={result.repo_a_name}
              nameB={result.repo_b_name}
            />
          ))}
        </div>
      </div>

      {/* All file matches summary */}
      {result.file_matches.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100">
            <h2 className="font-semibold text-gray-800">
              All File Pair Matches
              <span className="ml-2 text-xs font-normal text-gray-400">{result.file_matches.length} pairs across all methods</span>
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
                  <th className="px-4 py-2 text-left font-medium">File A</th>
                  <th className="px-4 py-2 text-left font-medium">File B</th>
                  <th className="px-4 py-2 text-right font-medium">Score</th>
                  <th className="px-4 py-2 text-left font-medium">Method</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {result.file_matches.map((fm, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-mono text-xs text-blue-700 max-w-xs truncate">{fm.file_a_path}</td>
                    <td className="px-4 py-2 font-mono text-xs text-orange-700 max-w-xs truncate">{fm.file_b_path}</td>
                    <td className="px-4 py-2 text-right"><Pct score={fm.similarity_score} /></td>
                    <td className="px-4 py-2 text-xs text-gray-500">{METHOD_NAMES[fm.method_id] ?? fm.method_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main app ───────────────────────────────────────────────────────────────────

export default function App() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [jobId, setJobId] = useState<string | null>(null);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  const [repoAName, setRepoAName] = useState("");
  const [repoBName, setRepoBName] = useState("");
  const [repoATab, setRepoATab] = useState<SourceTab>("git");
  const [repoBTab, setRepoBTab] = useState<SourceTab>("git");
  const [repoAUrl, setRepoAUrl] = useState("");
  const [repoBUrl, setRepoBUrl] = useState("");
  const [repoAPath, setRepoAPath] = useState("");
  const [repoBPath, setRepoBPath] = useState("");
  const [repoAFile, setRepoAFile] = useState<File | null>(null);
  const [repoBFile, setRepoBFile] = useState<File | null>(null);

  const pollJob = (id: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/compare/${id}`);
        if (!res.ok) { clearInterval(interval); setErrorMsg("Failed to poll job"); setPhase("error"); return; }
        const data = await res.json();
        if (data.status === "complete") { clearInterval(interval); setResult(data.result); setPhase("complete"); }
        else if (data.status === "failed") { clearInterval(interval); setErrorMsg(data.error ?? "Job failed"); setPhase("error"); }
      } catch { clearInterval(interval); setErrorMsg("Network error while polling"); setPhase("error"); }
    }, 2000);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPhase("running");
    setResult(null);
    setErrorMsg("");
    try {
      const useUpload = repoATab === "zip" || repoBTab === "zip";
      let res: Response;
      if (useUpload) {
        const form = new FormData();
        form.append("repo_a_name", repoAName || "Repo A");
        form.append("repo_b_name", repoBName || "Repo B");
        if (repoAFile) form.append("repo_a_zip", repoAFile);
        if (repoBFile) form.append("repo_b_zip", repoBFile);
        res = await fetch("/api/compare/upload", { method: "POST", body: form });
      } else {
        const src = (tab: SourceTab, url: string, path: string, name: string) => ({
          name: name || (tab === "git" ? (url.split("/").pop()?.replace(/\.git$/, "") ?? "repo") : (path.split("/").pop() ?? "repo")),
          source: tab as "git" | "local",
          url: tab === "git" ? url : undefined,
          path: tab === "local" ? path : undefined,
        });
        res = await fetch("/api/compare", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ repo_a: src(repoATab, repoAUrl, repoAPath, repoAName), repo_b: src(repoBTab, repoBUrl, repoBPath, repoBName) }),
        });
      }
      if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error((err as { detail?: string }).detail ?? `HTTP ${res.status}`); }
      const { job_id } = await res.json() as { job_id: string };
      setJobId(job_id);
      pollJob(job_id);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Unknown error");
      setPhase("error");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-5xl mx-auto">
          <h1 className="text-2xl font-bold text-gray-900">Code Compare</h1>
          <p className="text-sm text-gray-500 mt-0.5">Detect code similarity between two repositories using 9 analysis methods</p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-8">
        {(phase === "idle" || phase === "error") && (
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <RepoCard label="Repo A — Reference" accent="border-blue-200"
                name={repoAName} onNameChange={setRepoAName}
                tab={repoATab} onTabChange={setRepoATab}
                url={repoAUrl} onUrlChange={setRepoAUrl}
                path={repoAPath} onPathChange={setRepoAPath}
                file={repoAFile} onFileChange={setRepoAFile} />
              <RepoCard label="Repo B — Suspect" accent="border-orange-200"
                name={repoBName} onNameChange={setRepoBName}
                tab={repoBTab} onTabChange={setRepoBTab}
                url={repoBUrl} onUrlChange={setRepoBUrl}
                path={repoBPath} onPathChange={setRepoBPath}
                file={repoBFile} onFileChange={setRepoBFile} />
            </div>
            <div className="flex justify-end">
              <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-6 py-2 rounded-lg text-sm transition-colors">
                Run Comparison
              </button>
            </div>
            {phase === "error" && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
                <span className="font-semibold">Error: </span>{errorMsg}
              </div>
            )}
          </form>
        )}

        {phase === "running" && (
          <div className="bg-white border border-gray-200 rounded-xl p-10 text-center space-y-4">
            <div className="flex justify-center">
              <svg className="animate-spin h-10 w-10 text-blue-500" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
            </div>
            <p className="text-lg font-semibold text-gray-700">Analyzing repositories…</p>
            <p className="text-sm text-gray-500">Cloning, indexing, and running 9 analysis methods. This may take 1–3 minutes for large repos.</p>
            <p className="text-xs text-gray-400">Job ID: <code className="bg-gray-100 px-1.5 py-0.5 rounded">{jobId}</code></p>
          </div>
        )}

        {phase === "complete" && result && (
          <ResultsView result={result} onReset={() => { setPhase("idle"); setResult(null); }} />
        )}
      </main>
    </div>
  );
}

// Named exports for unit testing
export { scoreColor, scoreBg, scoreBar, Pct, MiniBar, CallGraphViz, SharedPills, FilePairDetail, MethodCard };
