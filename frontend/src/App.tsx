import { useState, useRef } from "react";

type Phase = "idle" | "running" | "complete" | "error";
type SourceTab = "git" | "local" | "zip";

interface MethodResult {
  method_id: string;
  score: number;
  weight: number;
  duration_ms: number;
  details: Record<string, unknown>;
}

interface FileMatch {
  file_a_path: string;
  file_b_path: string;
  similarity_score: number;
  method_id: string;
}

interface CompareResult {
  job_id: string;
  repo_a_name: string;
  repo_b_name: string;
  language: string;
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

function scoreColor(score: number): string {
  if (score < 0.4) return "text-green-600";
  if (score < 0.7) return "text-yellow-500";
  return "text-red-600";
}

function scoreBg(score: number): string {
  if (score < 0.4) return "bg-green-50 border-green-200";
  if (score < 0.7) return "bg-yellow-50 border-yellow-200";
  return "bg-red-50 border-red-200";
}

function ScoreBadge({ score }: { score: number }) {
  return (
    <span className={`font-semibold ${scoreColor(score)}`}>
      {(score * 100).toFixed(1)}%
    </span>
  );
}

interface RepoCardProps {
  label: string;
  accent: string;
  name: string;
  onNameChange: (v: string) => void;
  tab: SourceTab;
  onTabChange: (t: SourceTab) => void;
  url: string;
  onUrlChange: (v: string) => void;
  path: string;
  onPathChange: (v: string) => void;
  file: File | null;
  onFileChange: (f: File | null) => void;
}

function RepoCard({
  label,
  accent,
  name,
  onNameChange,
  tab,
  onTabChange,
  url,
  onUrlChange,
  path,
  onPathChange,
  file,
  onFileChange,
}: RepoCardProps) {
  const fileRef = useRef<HTMLInputElement>(null);

  const tabs: { id: SourceTab; label: string }[] = [
    { id: "git", label: "Git URL" },
    { id: "local", label: "Local Path" },
    { id: "zip", label: "Upload ZIP" },
  ];

  return (
    <div className={`border-2 ${accent} rounded-xl p-5 flex flex-col gap-4`}>
      <h3 className="font-semibold text-gray-700 text-sm uppercase tracking-wide">
        {label}
      </h3>

      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">
          Name
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          placeholder="e.g. project-alpha"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>

      <div className="flex gap-1 border border-gray-200 rounded-lg p-1 bg-gray-50">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => onTabChange(t.id)}
            className={`flex-1 text-xs py-1.5 rounded-md font-medium transition-colors ${
              tab === t.id
                ? "bg-white shadow text-blue-600"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "git" && (
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Git URL
          </label>
          <input
            type="text"
            value={url}
            onChange={(e) => onUrlChange(e.target.value)}
            placeholder="https://github.com/org/repo.git"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
      )}

      {tab === "local" && (
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Local Path
          </label>
          <input
            type="text"
            value={path}
            onChange={(e) => onPathChange(e.target.value)}
            placeholder="/path/to/repo"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
      )}

      {tab === "zip" && (
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            ZIP File
          </label>
          <div
            className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center cursor-pointer hover:border-blue-400 transition-colors"
            onClick={() => fileRef.current?.click()}
          >
            {file ? (
              <div className="text-sm text-gray-700">
                <span className="font-medium">{file.name}</span>
                <span className="text-gray-400 ml-2">
                  ({(file.size / 1024).toFixed(0)} KB)
                </span>
              </div>
            ) : (
              <p className="text-sm text-gray-400">
                Click to select a .zip file
              </p>
            )}
          </div>
          <input
            ref={fileRef}
            type="file"
            accept=".zip"
            className="hidden"
            onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
          />
        </div>
      )}
    </div>
  );
}

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
        if (!res.ok) {
          clearInterval(interval);
          setErrorMsg("Failed to poll job status");
          setPhase("error");
          return;
        }
        const data = await res.json();
        if (data.status === "complete") {
          clearInterval(interval);
          setResult(data.result);
          setPhase("complete");
        } else if (data.status === "failed") {
          clearInterval(interval);
          setErrorMsg(data.error ?? "Job failed");
          setPhase("error");
        }
      } catch {
        clearInterval(interval);
        setErrorMsg("Network error while polling");
        setPhase("error");
      }
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
        const buildSource = (tab: SourceTab, url: string, path: string, name: string) => ({
          name: name || (tab === "git" ? url.split("/").pop() ?? "repo" : path.split("/").pop() ?? "repo"),
          source: tab as "git" | "local",
          url: tab === "git" ? url : undefined,
          path: tab === "local" ? path : undefined,
        });

        const payload = {
          repo_a: buildSource(repoATab, repoAUrl, repoAPath, repoAName),
          repo_b: buildSource(repoBTab, repoBUrl, repoBPath, repoBName),
          language,
        };
        res = await fetch("/api/compare", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      }

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `HTTP ${res.status}`);
      }

      const { job_id } = await res.json();
      setJobId(job_id);
      pollJob(job_id);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Unknown error");
      setPhase("error");
    }
  };

  const handleDownload = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `comparison_${result.job_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-5xl mx-auto">
          <h1 className="text-2xl font-bold text-gray-900">Code Compare</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Detect code similarity between two repositories using 9 analysis methods
          </p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-8">
        {/* Form */}
        {(phase === "idle" || phase === "error") && (
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <RepoCard
                label="Repo A — Reference"
                accent="border-blue-200"
                name={repoAName}
                onNameChange={setRepoAName}
                tab={repoATab}
                onTabChange={setRepoATab}
                url={repoAUrl}
                onUrlChange={setRepoAUrl}
                path={repoAPath}
                onPathChange={setRepoAPath}
                file={repoAFile}
                onFileChange={setRepoAFile}
              />
              <RepoCard
                label="Repo B — Suspect"
                accent="border-orange-200"
                name={repoBName}
                onNameChange={setRepoBName}
                tab={repoBTab}
                onTabChange={setRepoBTab}
                url={repoBUrl}
                onUrlChange={setRepoBUrl}
                path={repoBPath}
                onPathChange={setRepoBPath}
                file={repoBFile}
                onFileChange={setRepoBFile}
              />
            </div>

            <div className="flex items-center gap-4 bg-white border border-gray-200 rounded-xl px-5 py-4">
              <label className="text-sm font-medium text-gray-700 whitespace-nowrap">
                Language
              </label>
              <select
                value={language}
                onChange={(e) =>
                  setLanguage(e.target.value as "python" | "javascript")
                }
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              >
                <option value="python">Python</option>
                <option value="javascript">JavaScript / TypeScript</option>
              </select>

              <div className="flex-1" />

              <button
                type="submit"
                className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-6 py-2 rounded-lg text-sm transition-colors"
              >
                Run Comparison
              </button>
            </div>

            {phase === "error" && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
                <span className="font-semibold">Error: </span>
                {errorMsg}
              </div>
            )}
          </form>
        )}

        {/* Running */}
        {phase === "running" && (
          <div className="bg-white border border-gray-200 rounded-xl p-10 text-center space-y-4">
            <div className="flex justify-center">
              <svg
                className="animate-spin h-10 w-10 text-blue-500"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8v8H4z"
                />
              </svg>
            </div>
            <p className="text-lg font-semibold text-gray-700">Analyzing…</p>
            <p className="text-sm text-gray-500">
              This may take a minute. Job ID:{" "}
              <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs">
                {jobId}
              </code>
            </p>
          </div>
        )}

        {/* Results */}
        {phase === "complete" && result && (
          <div className="space-y-6">
            {/* Overall score card */}
            <div
              className={`border-2 rounded-xl p-8 text-center ${scoreBg(result.overall_score)}`}
            >
              <div
                className={`text-6xl font-bold ${scoreColor(result.overall_score)}`}
              >
                {(result.overall_score * 100).toFixed(1)}%
              </div>
              <div className="text-lg font-semibold text-gray-700 mt-2">
                Similarity Score
              </div>
              <div className="text-sm text-gray-500 mt-1">
                {result.repo_a_name} vs {result.repo_b_name}
              </div>
              <div className="flex gap-3 justify-center mt-5">
                <button
                  onClick={handleDownload}
                  className="bg-white border border-gray-300 hover:border-gray-400 text-gray-700 text-sm font-medium px-4 py-2 rounded-lg transition-colors"
                >
                  Download JSON Report
                </button>
                <button
                  onClick={() => {
                    setPhase("idle");
                    setResult(null);
                  }}
                  className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
                >
                  New Comparison
                </button>
              </div>
            </div>

            {/* Method breakdown */}
            <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
              <div className="px-5 py-3 border-b border-gray-100">
                <h2 className="font-semibold text-gray-800">Method Breakdown</h2>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
                    <th className="px-5 py-3 font-medium">Method</th>
                    <th className="px-5 py-3 font-medium text-right">Score</th>
                    <th className="px-5 py-3 font-medium text-right">Weight</th>
                    <th className="px-5 py-3 font-medium text-right">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {result.methods.map((m) => (
                    <tr key={m.method_id} className="hover:bg-gray-50">
                      <td className="px-5 py-3 font-medium text-gray-700">
                        {METHOD_NAMES[m.method_id] ?? m.method_id}
                      </td>
                      <td className="px-5 py-3 text-right">
                        <ScoreBadge score={m.score} />
                      </td>
                      <td className="px-5 py-3 text-right text-gray-500">
                        {(m.weight * 100).toFixed(1)}%
                      </td>
                      <td className="px-5 py-3 text-right text-gray-400">
                        {m.duration_ms}ms
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* File matches */}
            {result.file_matches.length > 0 && (
              <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                <div className="px-5 py-3 border-b border-gray-100">
                  <h2 className="font-semibold text-gray-800">
                    Top File Matches
                    <span className="ml-2 text-xs font-normal text-gray-400">
                      (top {Math.min(result.file_matches.length, 20)} of{" "}
                      {result.file_matches.length})
                    </span>
                  </h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
                        <th className="px-5 py-3 font-medium">File A</th>
                        <th className="px-5 py-3 font-medium">File B</th>
                        <th className="px-5 py-3 font-medium text-right">
                          Score
                        </th>
                        <th className="px-5 py-3 font-medium">Method</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {result.file_matches.slice(0, 20).map((fm, i) => (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="px-5 py-2.5 text-gray-600 font-mono text-xs max-w-xs truncate">
                            {fm.file_a_path}
                          </td>
                          <td className="px-5 py-2.5 text-gray-600 font-mono text-xs max-w-xs truncate">
                            {fm.file_b_path}
                          </td>
                          <td className="px-5 py-2.5 text-right">
                            <ScoreBadge score={fm.similarity_score} />
                          </td>
                          <td className="px-5 py-2.5 text-gray-500 text-xs">
                            {METHOD_NAMES[fm.method_id] ?? fm.method_id}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
