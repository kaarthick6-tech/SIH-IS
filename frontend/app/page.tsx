"use client";

import { useRef, useState } from "react";
import {
  AlertCircle,
  BadgeCheck,
  FileText,
  FileUp,
  Layers,
  Loader2,
  Scale,
  ShieldAlert,
  Sparkles,
  X,
} from "lucide-react";
import {
  analyzeDocument,
  analyzeSpecification,
  MAX_PDF_BYTES,
  type AnalyzeResponse,
  type Confidence,
} from "@/lib/api";

const EXAMPLE_QUERY =
  "High strength deformed steel bars, Fe500D grade, for coastal bridge construction";

type InputMode = "text" | "file";

const ALLIED_LABELS: Record<string, string> = {
  test_methods: "Test Methods",
  terminology: "Terminology",
  safety: "Safety",
  installation: "Installation",
};

const CONFIDENCE_STYLES: Record<Confidence, string> = {
  High: "border-emerald-200 bg-emerald-50 text-emerald-700",
  Medium: "border-amber-200 bg-amber-50 text-amber-800",
  Low: "border-red-200 bg-red-50 text-red-700",
};

function labelFor(key: string) {
  return (
    ALLIED_LABELS[key] ??
    key.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase())
  );
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function Home() {
  const [mode, setMode] = useState<InputMode>("text");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function resetResults() {
    setError(null);
    setData(null);
    setFileError(null);
  }

  function switchMode(next: InputMode) {
    setMode(next);
    resetResults();
  }

  function pickFile(candidate: File | null) {
    resetResults();
    if (!candidate) return;
    if (!candidate.name.toLowerCase().endsWith(".pdf")) {
      setFile(null);
      setFileError("Only PDF files are supported.");
      return;
    }
    if (candidate.size > MAX_PDF_BYTES) {
      setFile(null);
      setFileError(
        `That file is ${formatSize(candidate.size)}. The limit is 20 MB.`,
      );
      return;
    }
    setFile(candidate);
  }

  async function handleTextSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = text.trim();
    if (!query) return;
    resetResults();
    setLoading(true);
    try {
      setData(await analyzeSpecification(query));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  async function handleFileSubmit() {
    if (!file) return;
    resetResults();
    setLoading(true);
    try {
      setData(await analyzeDocument(file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  const mandatory = (data?.certifications ?? []).filter((c) => c.mandatory);
  const alliedGroups = data
    ? Object.entries(data.allied_standards).filter(([, items]) => items.length > 0)
    : [];

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex w-full max-w-5xl items-center gap-3 px-6 py-4">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm">
            <Scale className="h-5 w-5" aria-hidden="true" />
          </span>
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-slate-900">
              StandardsCopilot
            </h1>
            <p className="text-xs text-slate-500">
              AI-powered Indian Standards matching for procurement requirements
            </p>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-10">
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div
            role="tablist"
            aria-label="Input type"
            className="inline-flex rounded-lg border border-slate-200 bg-slate-100/70 p-1"
          >
            {(
              [
                { id: "text" as const, label: "Paste Text", icon: FileText },
                { id: "file" as const, label: "Upload PDF", icon: FileUp },
              ]
            ).map((tab) => {
              const Icon = tab.icon;
              const active = mode === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  onClick={() => switchMode(tab.id)}
                  className={`inline-flex items-center gap-2 rounded-md px-4 py-1.5 text-sm font-medium transition ${
                    active
                      ? "bg-white text-indigo-700 shadow-sm"
                      : "text-slate-500 hover:text-slate-700"
                  }`}
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  {tab.label}
                </button>
              );
            })}
          </div>

          {mode === "text" ? (
            <form onSubmit={handleTextSubmit} className="mt-5">
              <label
                htmlFor="spec"
                className="text-sm font-semibold text-slate-900"
              >
                Product description or tender specification
              </label>
              <p className="mt-1 text-sm text-slate-500">
                Paste a requirement - material grade, application, or test method.
              </p>

              <textarea
                id="spec"
                rows={5}
                value={text}
                onChange={(event) => setText(event.target.value)}
                placeholder={EXAMPLE_QUERY}
                className="mt-4 w-full resize-y rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm leading-relaxed text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:bg-white focus:ring-2 focus:ring-indigo-100 focus:outline-none"
              />

              <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={() => setText(EXAMPLE_QUERY)}
                  className="text-xs font-medium text-indigo-600 hover:text-indigo-700"
                >
                  Use example
                </button>
                <button
                  type="submit"
                  disabled={loading || text.trim().length === 0}
                  className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-200 focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:bg-slate-300"
                >
                  {loading ? (
                    <>
                      <Loader2
                        className="h-4 w-4 animate-spin"
                        aria-hidden="true"
                      />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4" aria-hidden="true" />
                      Get Recommendations
                    </>
                  )}
                </button>
              </div>
            </form>
          ) : (
            <div className="mt-5">
              <p className="text-sm font-semibold text-slate-900">
                Upload a specification document
              </p>
              <p className="mt-1 text-sm text-slate-500">
                We extract the text and match it against the standards catalog.
              </p>

              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                className="hidden"
                onChange={(event) =>
                  pickFile(event.target.files?.[0] ?? null)
                }
              />

              {file ? (
                <div className="mt-4 flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                    <FileUp className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-slate-900">
                      {file.name}
                    </p>
                    <p className="text-xs text-slate-500">
                      {formatSize(file.size)} Â· PDF
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setFile(null);
                      resetResults();
                      if (fileInputRef.current) {
                        fileInputRef.current.value = "";
                      }
                    }}
                    className="rounded-md p-1.5 text-slate-400 transition hover:bg-slate-200 hover:text-slate-600"
                    aria-label="Remove file"
                  >
                    <X className="h-4 w-4" aria-hidden="true" />
                  </button>
                </div>
              ) : (
                <div
                  role="button"
                  tabIndex={0}
                  onClick={() => fileInputRef.current?.click()}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      fileInputRef.current?.click();
                    }
                  }}
                  onDragOver={(event) => {
                    event.preventDefault();
                    setDragging(true);
                  }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={(event) => {
                    event.preventDefault();
                    setDragging(false);
                    pickFile(event.dataTransfer.files?.[0] ?? null);
                  }}
                  className={`mt-4 cursor-pointer rounded-lg border-2 border-dashed p-10 text-center transition ${
                    dragging
                      ? "border-indigo-400 bg-indigo-50"
                      : "border-slate-300 bg-slate-50 hover:border-indigo-300 hover:bg-slate-100"
                  }`}
                >
                  <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50 text-indigo-600">
                    <FileUp className="h-6 w-6" aria-hidden="true" />
                  </span>
                  <p className="mt-3 text-sm font-semibold text-slate-900">
                    Click to upload or drag and drop a PDF
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Maximum 20 MB. Scanned PDFs need OCR before they can be read.
                  </p>
                </div>
              )}

              {fileError && (
                <p className="mt-3 flex items-center gap-2 text-sm text-red-600">
                  <AlertCircle className="h-4 w-4" aria-hidden="true" />
                  {fileError}
                </p>
              )}

              <div className="mt-4 flex justify-end">
                <button
                  type="button"
                  onClick={handleFileSubmit}
                  disabled={loading || !file}
                  className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-200 focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:bg-slate-300"
                >
                  {loading ? (
                    <>
                      <Loader2
                        className="h-4 w-4 animate-spin"
                        aria-hidden="true"
                      />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4" aria-hidden="true" />
                      Analyze Document
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {loading && (
            <p className="mt-4 rounded-lg border border-indigo-100 bg-indigo-50 px-4 py-3 text-sm text-indigo-700">
              Extracting text, searching with semantic vectors, then reranking
              with an LLM. The first request loads the AI model and can take up
              to a minute.
            </p>
          )}
        </div>

        {error && (
          <div className="mt-6 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4">
            <AlertCircle
              className="mt-0.5 h-5 w-5 shrink-0 text-red-600"
              aria-hidden="true"
            />
            <div>
              <p className="text-sm font-semibold text-red-900">Request failed</p>
              <p className="mt-1 text-sm text-red-700">{error}</p>
            </div>
          </div>
        )}

        {data && (
          <div className="mt-8 space-y-8">
            {mandatory.length > 0 && (
              <div className="rounded-xl border border-red-200 bg-red-50 p-5">
                <div className="flex items-start gap-3">
                  <ShieldAlert
                    className="mt-0.5 h-5 w-5 shrink-0 text-red-600"
                    aria-hidden="true"
                  />
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wide text-red-700">
                      Mandatory Certification Required
                    </p>
                    <p className="mt-1 text-base font-semibold text-red-900">
                      {mandatory.map((c) => c.scheme_name).join(", ")}
                    </p>
                    <ul className="mt-2 space-y-1 text-sm text-red-700">
                      {mandatory
                        .filter((c) => c.notes)
                        .map((c) => (
                          <li key={c.scheme_name}>{c.notes}</li>
                        ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            <section>
              <h2 className="text-base font-semibold text-slate-900">
                Primary Recommendations
              </h2>

              {data.justification &&
                data.primary_recommendations.length > 0 && (
                  <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
                    <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
                      <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                      Why this matches
                    </p>
                    <p className="mt-1.5 text-sm leading-relaxed text-slate-700">
                      {data.justification}
                    </p>
                  </div>
                )}
              {data.primary_recommendations.length === 0 ? (
                <p className="mt-3 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-500 shadow-sm">
                  No standards matched this requirement.
                </p>
              ) : (
                <div className="mt-3 space-y-4">
                  {data.primary_recommendations.map((rec) => (
                    <article
                      key={rec.is_number}
                      className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="font-mono text-sm font-semibold text-indigo-600">
                            {rec.is_number}
                          </p>
                          <h3 className="mt-1 flex items-start gap-2 text-base font-semibold text-slate-900">
                            <FileText
                              className="mt-0.5 h-4 w-4 shrink-0 text-slate-400"
                              aria-hidden="true"
                            />
                            {rec.title}
                          </h3>
                        </div>
                        <span
                          className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                            CONFIDENCE_STYLES[rec.confidence] ??
                            CONFIDENCE_STYLES.Low
                          }`}
                        >
                          {rec.confidence} confidence
                        </span>
                      </div>

                      <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 border-t border-slate-100 pt-3 text-xs text-slate-500">
                        <span className="inline-flex items-center gap-1">
                          <BadgeCheck className="h-3.5 w-3.5" aria-hidden="true" />
                          Status: {rec.status ?? "Unknown"}
                        </span>
                        <span>
                          Latest amendment: {rec.latest_amendment ?? "Not recorded"}
                        </span>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>

            {alliedGroups.length > 0 && (
              <section>
                <h2 className="flex items-center gap-2 text-base font-semibold text-slate-900">
                  <Layers className="h-4 w-4 text-slate-400" aria-hidden="true" />
                  Allied Standards
                </h2>
                <div className="mt-3 grid gap-4 sm:grid-cols-2">
                  {alliedGroups.map(([key, items]) => (
                    <div
                      key={key}
                      className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
                    >
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        {labelFor(key)}
                      </p>
                      <ul className="mt-3 space-y-2">
                        {items.map((item) => (
                          <li key={item.is_number} className="text-sm">
                            <span className="font-mono font-semibold text-indigo-600">
                              {item.is_number}
                            </span>
                            <span className="block text-slate-600">{item.title}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </div>
        )}
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto w-full max-w-5xl px-6 py-5">
          <p className="text-xs leading-relaxed text-slate-400">
            Recommendations are based on publicly available metadata. Always verify
            against the official BIS catalog.
          </p>
        </div>
      </footer>
    </div>
  );
}
