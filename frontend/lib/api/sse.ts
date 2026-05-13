/**
 * Minimal Server-Sent Events consumer over fetch.
 *
 * EventSource (the browser native) only supports GET and cannot send custom
 * headers (including Authorization). We use fetch + ReadableStream + a simple
 * line-by-line parser instead.
 *
 * Wire format expected (matches FastAPI's StreamingResponse from
 * /v1/expression/correct):
 *
 *     event: <name>\n
 *     data: <JSON>\n
 *     \n   (blank line marks end of event)
 */

export type SseEvent<T = unknown> = {
  event: string;
  data: T;
};

export type StreamHandlers<T> = {
  onEvent: (event: SseEvent<T>) => void;
  onError?: (error: Error) => void;
  onDone?: () => void;
  signal?: AbortSignal;
};

export async function streamSse<T = unknown>(
  url: string,
  init: RequestInit,
  handlers: StreamHandlers<T>
): Promise<void> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "text/event-stream");
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...init,
      headers,
      signal: handlers.signal,
    });
  } catch (error) {
    handlers.onError?.(error instanceof Error ? error : new Error("Network error"));
    return;
  }

  if (!response.ok || !response.body) {
    let detail = "";
    try {
      const json = await response.json();
      detail = typeof json?.detail === "string" ? json.detail : JSON.stringify(json);
    } catch {
      detail = response.statusText;
    }
    handlers.onError?.(new Error(`${response.status}: ${detail}`));
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let separatorIndex: number;
      while ((separatorIndex = buffer.indexOf("\n\n")) !== -1) {
        const rawEvent = buffer.slice(0, separatorIndex);
        buffer = buffer.slice(separatorIndex + 2);
        const parsed = parseSseBlock(rawEvent);
        if (parsed) {
          try {
            handlers.onEvent({
              event: parsed.event,
              data: JSON.parse(parsed.data) as T,
            });
          } catch (err) {
            handlers.onError?.(err instanceof Error ? err : new Error("Bad JSON in SSE data"));
          }
        }
      }
    }
    handlers.onDone?.();
  } catch (error) {
    if ((error as Error).name === "AbortError") {
      handlers.onDone?.();
      return;
    }
    handlers.onError?.(error instanceof Error ? error : new Error("Stream error"));
  } finally {
    reader.releaseLock();
  }
}

function parseSseBlock(raw: string): { event: string; data: string } | null {
  let event = "message";
  const dataLines: string[] = [];

  for (const line of raw.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }

  if (dataLines.length === 0) return null;
  return { event, data: dataLines.join("\n") };
}
