/**
 * Minimal incremental Server-Sent Events parser.
 *
 * The Fetch streaming API hands us arbitrary byte chunks, not whole SSE frames.
 * `push` buffers across chunks and returns whatever complete `event`/`data`
 * frames (separated by a blank line) have arrived; `flush` drains any trailing
 * frame that wasn't newline-terminated. Only the `event` name and `data` payload
 * are surfaced — `id`/`retry`/comments are ignored (unused by our endpoints).
 */

export interface SSEEvent {
  event: string | null;
  data: string;
}

function parseFrame(rawFrame: string): SSEEvent | null {
  let event: string | null = null;
  const dataLines: string[] = [];

  for (const line of rawFrame.split("\n")) {
    if (!line || line.startsWith(":")) continue; // blank or comment line
    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    // Per the SSE spec, a single leading space after the colon is stripped.
    let value = colon === -1 ? "" : line.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);

    if (field === "event") event = value;
    else if (field === "data") dataLines.push(value);
  }

  if (event === null && dataLines.length === 0) return null;
  return { event, data: dataLines.join("\n") };
}

export interface SSEParser {
  push(chunk: string): SSEEvent[];
  flush(): SSEEvent[];
}

export function createSSEParser(): SSEParser {
  let buffer = "";

  return {
    push(chunk: string): SSEEvent[] {
      buffer += chunk.replace(/\r\n/g, "\n");
      const events: SSEEvent[] = [];
      let idx: number;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const rawFrame = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        const parsed = parseFrame(rawFrame);
        if (parsed) events.push(parsed);
      }
      return events;
    },
    flush(): SSEEvent[] {
      const rest = buffer.trim();
      buffer = "";
      if (!rest) return [];
      const parsed = parseFrame(rest);
      return parsed ? [parsed] : [];
    },
  };
}
