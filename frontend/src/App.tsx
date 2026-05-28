import { useState, useRef } from "react";

type Phase = "idle" | "running" | "complete" | "error";
type SourceTab = "git" | "local" | "zip";

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
    <div className="flex items-center gap-2">
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
  const tabs: { id: SourceTab; label: string }[] = [
    { id: "git", label: "Git URL" },
    { id: "local", label: "Local Path" },
    { id: "zip", label: "Upload ZIP" },
  ];
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
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Local Path</label>
          <input type="text" value={path} onChange={e => onPathChange(e.target.value)} placeholder="/path/to/repo"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
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

// ── Method detail panel ────────────────────────────────────────────────────────

function MethodDetail({ method, matches }: { method: MethodResult; matches: FileMatch[] }) {
  const [open, setOpen] = useState(false);
  const d = method.details;

  const sharedNames = (d.shared_names as string[] | undefined) ?? [];
  const sharedImports = (d.shared_imports as string[] | undefined) ?? [];
  const sharedIds = (d.shared_identifiers as string[] | undefined) ?? [];
  const hasDetail = sharedNames.length > 0 || sharedImports.length > 0 || sharedIds.length > 0 || matches.length > 0;
  if (!hasDetail) return null;

  return (
    <div className="border-t border-gray-100">
      <button type="button" onClick={() => setOpen(o => !o)}
        className="w-full text-left px-5 py-2 text-xs text-blue-600 hover:bg-blue-50 flex items-center gap-1">
        <span>{open ? "▾" : "▸"}</span>
        <span>{open ? "Hide detail" : `Show detail${matches.length > 0 ? ` — ${matches.length} file pair${matches.length > 1 ? "s" : ""}` : ""}`}</span>
      </button>
      {open && (
        <div className="px-5 pb-4 space-y-3">
          {/* Shared lists */}
          {sharedNames.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 mb-1">Shared function/class names ({sharedNames.length})</p>
              <div className="flex flex-wrap gap-1">
                {sharedNames.map(n => <code key={n} className="text-xs bg-orange-50 text-orange-700 border border-orange-200 rounded px-1.5 py-0.5">{n}</code>)}
              </div>
            </div>
          )}
          {sharedImports.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 mb-1">Shared imports ({sharedImports.length})</p>
              <div className="flex flex-wrap gap-1">
                {sharedImports.map(n => <code key={n} className="text-xs bg-purple-50 text-purple-700 border border-purple-200 rounded px-1.5 py-0.5">{n}</code>)}
              </div>
            </div>
          )}
          {sharedIds.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 mb-1">Shared identifiers ({sharedIds.length})</p>
              <div className="flex flex-wrap gap-1 max-h-20 overflow-y-auto">
                {sharedIds.map(n => <code key={n} className="text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded px-1.5 py-0.5">{n}</code>)}
              </div>
            </div>
          )}
          {/* File pair matches */}
          {matches.length > 0 && (
            <div className="space-y-3">
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

// ── File pair detail ──────────────────────────────────────────────────────────

function FilePairDetail({ fm }: { fm: FileMatch }) {
  const blocks = fm.detail?.matching_blocks ?? [];
  const sharedFns = fm.detail?.shared_functions ?? [];

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between bg-gray-50 px-3 py-2 text-xs">
        <div className="flex items-center gap-2 min-w-0">
          <code className="text-blue-700 truncate max-w-xs">{fm.file_a_path}</code>
          <span className="text-gray-400 shrink-0">↔</span>
          <code className="text-orange-700 truncate max-w-xs">{fm.file_b_path}</code>
        </div>
        <Pct score={fm.similarity_score} />
      </div>

      {/* Shared function names for this file pair */}
      {sharedFns.length > 0 && (
        <div className="px-3 py-2 border-t border-gray-100">
          <p className="text-xs text-gray-500 mb-1">Shared functions in this pair:</p>
          <div className="flex flex-wrap gap-1">
            {sharedFns.map(fn => <code key={fn} className="text-xs bg-orange-50 text-orange-700 border border-orange-200 rounded px-1.5 py-0.5">{fn}</code>)}
          </div>
        </div>
      )}

      {/* Matching code blocks */}
      {blocks.length > 0 && (
        <div className="divide-y divide-gray-100">
          {blocks.map((b, i) => (
            <div key={i} className="px-3 py-2">
              <div className="flex gap-4 text-xs text-gray-400 mb-1">
                <span>A line {b.a_line_start}–{b.a_line_start + b.length - 1}</span>
                <span>B line {b.b_line_start}–{b.b_line_start + b.length - 1}</span>
                <span>({b.length} lines)</span>
              </div>
              <pre className="text-xs bg-gray-900 text-green-400 rounded p-2 overflow-x-auto max-h-32">{b.lines.join("\n")}</pre>
            </div>
          ))}
        </div>
      )}

      {/* Generic detail fallback */}
      {blocks.length === 0 && sharedFns.length === 0 && Object.keys(fm.detail ?? {}).length > 0 && (
        <div className="px-3 py-2 border-t border-gray-100">
          <pre className="text-xs text-gray-500 whitespace-pre-wrap">{JSON.stringify(fm.detail, null, 2)}</pre>
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
            No {result.language} files found — check the language selector matches the repos.
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
          <p className="text-xs text-gray-400 mt-0.5">Click "Show detail" under each method to see what matched</p>
        </div>
        <div className="divide-y divide-gray-100">
          {result.methods.map(m => (
            <div key={m.method_id}>
              <div className="px-5 py-3 flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-800 text-sm">{METHOD_NAMES[m.method_id] ?? m.method_id}</span>
                    <span className="text-xs text-gray-400 font-normal">{(m.weight * 100).toFixed(0)}% weight</span>
                    <span className="text-xs text-gray-300">{m.duration_ms}ms</span>
                    {m.details.error != null && <span className="text-xs text-red-500">⚠ error</span>}
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5">{METHOD_DESC[m.method_id]}</p>
                </div>
                <MiniBar score={m.score} />
              </div>
              <MethodDetail method={m} matches={matchesByMethod[m.method_id] ?? []} />
            </div>
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
  const [language, setLanguage] = useState<"python" | "javascript">("python");

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
        form.append("language", language);
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
          body: JSON.stringify({ repo_a: src(repoATab, repoAUrl, repoAPath, repoAName), repo_b: src(repoBTab, repoBUrl, repoBPath, repoBName), language }),
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
            <div className="flex items-center gap-4 bg-white border border-gray-200 rounded-xl px-5 py-4">
              <label className="text-sm font-medium text-gray-700 whitespace-nowrap">Language</label>
              <select value={language} onChange={e => setLanguage(e.target.value as "python" | "javascript")}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
                <option value="python">Python (.py)</option>
                <option value="javascript">JavaScript / TypeScript (.js .ts .jsx .tsx)</option>
              </select>
              <div className="flex-1" />
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
