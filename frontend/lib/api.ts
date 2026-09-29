/**
 * Typed client for the FastAPI backend.
 *
 *   POST /api/analyze       - JSON body  { "text": "..." }
 *   POST /api/analyze-file  - multipart form field "file" (PDF)
 *
 * Set NEXT_PUBLIC_API_URL to override the backend base URL (defaults to localhost:8000).
 */

export type Confidence = "High" | "Medium" | "Low";

export interface PrimaryRecommendation {
  is_number: string;
  title: string;
  status: string | null;
  latest_amendment: string | null;
  confidence: Confidence;
}

export interface AlliedStandard {
  is_number: string;
  title: string;
}

export interface Certification {
  scheme_name: string;
  mandatory: boolean;
  notes: string | null;
}

export interface AnalyzeResponse {
  /** One shared rationale from the LLM for the whole selection. */
  justification: string;
  primary_recommendations: PrimaryRecommendation[];
  allied_standards: Record<string, AlliedStandard[]>;
  certifications: Certification[];
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const TEXT_ENDPOINT = `${API_BASE}/api/analyze`;
const FILE_ENDPOINT = `${API_BASE}/api/analyze-file`;

/**
 * The backend lazily loads the BAAI/bge-m3 model on the first request, so the
 * very first call can take a while. Keep the timeout generous.
 */
const TIMEOUT_MS = 180_000;

export const MAX_PDF_BYTES = 20 * 1024 * 1024; // must match the backend limit

/** FastAPI returns {"detail": "..."} - surface that instead of raw JSON. */
async function readErrorMessage(response: Response): Promise<string> {
  const fallback = `The backend returned HTTP ${response.status}.`;
  try {
    const body = await response.text();
    if (!body) return fallback;
    try {
      const parsed = JSON.parse(body) as { detail?: string };
      if (typeof parsed.detail === "string") return parsed.detail;
    } catch {
      /* not JSON - fall through to the raw text */
    }
    return body.slice(0, 300);
  } catch {
    return fallback;
  }
}

function wrapError(error: unknown, endpoint: string, timedOut: boolean): Error {
  if (timedOut) {
    return new Error(
      "The request timed out after 3 minutes. The first analysis loads the AI model, which can be slow - please try again.",
    );
  }
  if (error instanceof TypeError) {
    return new Error(
      `Could not reach the backend at ${endpoint}. Make sure it is running (uvicorn main:app --reload).`,
    );
  }
  return error instanceof Error ? error : new Error("Unexpected error.");
}

export async function analyzeSpecification(
  text: string,
): Promise<AnalyzeResponse> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const response = await fetch(TEXT_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }

    return (await response.json()) as AnalyzeResponse;
  } catch (error) {
    throw wrapError(error, TEXT_ENDPOINT, controller.signal.aborted);
  } finally {
    clearTimeout(timer);
  }
}

export async function analyzeDocument(file: File): Promise<AnalyzeResponse> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  const form = new FormData();
  form.append("file", file);

  try {
    const response = await fetch(FILE_ENDPOINT, {
      method: "POST",
      // Deliberately no Content-Type header: the browser must set the
      // multipart/form-data boundary itself.
      body: form,
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }

    return (await response.json()) as AnalyzeResponse;
  } catch (error) {
    throw wrapError(error, FILE_ENDPOINT, controller.signal.aborted);
  } finally {
    clearTimeout(timer);
  }
}
