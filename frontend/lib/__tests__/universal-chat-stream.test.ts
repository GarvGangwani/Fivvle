import { describe, expect, it, vi } from "vitest";

import { createSSEParser } from "../sse-parser";
import { tokenizeCitations } from "../parse-citations";

/**
 * Mirrors streamUniversalChatMessage dispatch logic against canned SSE frames.
 */
function dispatchUniversalFrames(
  raw: string,
  callbacks: {
    onToolCall: (p: { tool_name: string; message_id: string }) => void;
    onToolResult: (p: {
      tool_name: string;
      message_id: string;
      payload: Record<string, unknown>;
    }) => void;
    onSubagentToken: (p: { agent: "refine" | "research"; text: string }) => void;
    onAssistantToken: (p: { text: string }) => void;
    onDone: (p: {
      assistant_message_id: string;
      thread_id: string;
      user_message_id?: string;
    }) => void;
    onError: (message: string) => void;
  },
): void {
  const parser = createSSEParser();
  for (const event of [...parser.push(raw), ...parser.flush()]) {
    if (event.event === "tool_call") {
      const data = JSON.parse(event.data) as {
        tool_name: string;
        message_id: string;
      };
      callbacks.onToolCall(data);
    } else if (event.event === "tool_result") {
      const data = JSON.parse(event.data) as {
        tool_name: string;
        message_id: string;
        payload?: Record<string, unknown>;
      };
      callbacks.onToolResult({
        tool_name: data.tool_name,
        message_id: data.message_id,
        payload: data.payload ?? {},
      });
    } else if (event.event === "subagent_token") {
      const data = JSON.parse(event.data) as {
        agent: "refine" | "research";
        text: string;
      };
      callbacks.onSubagentToken(data);
    } else if (event.event === "assistant_token") {
      const data = JSON.parse(event.data) as { text: string };
      callbacks.onAssistantToken(data);
    } else if (event.event === "done") {
      const data = JSON.parse(event.data) as {
        assistant_message_id: string;
        thread_id: string;
        user_message_id?: string;
      };
      callbacks.onDone(data);
    } else if (event.event === "error") {
      const data = JSON.parse(event.data) as { message?: string };
      callbacks.onError(data.message ?? "error");
    }
  }
}

describe("universal chat SSE dispatch", () => {
  it("dispatches tokens before tool_result with payload", () => {
    const calls: string[] = [];
    let lastPayload: Record<string, unknown> | null = null;
    const frames = [
      'event: tool_call\ndata: {"tool_name":"ask_research_agent","message_id":"tc1"}\n\n',
      'event: subagent_token\ndata: {"agent":"research","text":"Hello "}\n\n',
      'event: subagent_token\ndata: {"agent":"research","text":"[cite:s1]"}\n\n',
      'event: tool_result\ndata: {"tool_name":"ask_research_agent","message_id":"tr1","payload":{"tool_name":"ask_research_agent","result":{"assistant_text_with_citations":"Hello [cite:s1]","source_refs":[{"marker_id":"[cite:s1]","source_title":"Ex","source_url":"https://ex.com","source_domain":"ex.com"}]}}}\n\n',
      'event: assistant_token\ndata: {"text":"Master wrap."}\n\n',
      'event: done\ndata: {"assistant_message_id":"a1","thread_id":"th1"}\n\n',
    ].join("");

    dispatchUniversalFrames(frames, {
      onToolCall: (p) => calls.push(`tool_call:${p.tool_name}`),
      onToolResult: (p) => {
        calls.push(`tool_result:${p.message_id}`);
        lastPayload = p.payload;
      },
      onSubagentToken: (p) => calls.push(`sub:${p.agent}:${p.text}`),
      onAssistantToken: (p) => calls.push(`asst:${p.text}`),
      onDone: (p) => calls.push(`done:${p.assistant_message_id}`),
      onError: (m) => calls.push(`error:${m}`),
    });

    expect(calls).toEqual([
      "tool_call:ask_research_agent",
      "sub:research:Hello ",
      "sub:research:[cite:s1]",
      "tool_result:tr1",
      "asst:Master wrap.",
      "done:a1",
    ]);
    expect(lastPayload).toMatchObject({
      tool_name: "ask_research_agent",
      result: {
        assistant_text_with_citations: "Hello [cite:s1]",
        source_refs: [
          expect.objectContaining({ marker_id: "[cite:s1]", source_domain: "ex.com" }),
        ],
      },
    });
  });

  it("done is a terminal signal without requiring refetch semantics", () => {
    const onDone = vi.fn();
    const onToolResult = vi.fn();
    dispatchUniversalFrames(
      [
        'event: assistant_token\ndata: {"text":"Hi"}\n\n',
        'event: done\ndata: {"assistant_message_id":"a1","thread_id":"th1","user_message_id":"u1"}\n\n',
      ].join(""),
      {
        onToolCall: vi.fn(),
        onToolResult,
        onSubagentToken: vi.fn(),
        onAssistantToken: vi.fn(),
        onDone,
        onError: vi.fn(),
      },
    );
    expect(onDone).toHaveBeenCalledWith({
      assistant_message_id: "a1",
      thread_id: "th1",
      user_message_id: "u1",
    });
    expect(onToolResult).not.toHaveBeenCalled();
  });

  it("dispatches error frames", () => {
    const onError = vi.fn();
    dispatchUniversalFrames(
      'event: error\ndata: {"message":"Universal chat failed, please try again"}\n\n',
      {
        onToolCall: vi.fn(),
        onToolResult: vi.fn(),
        onSubagentToken: vi.fn(),
        onAssistantToken: vi.fn(),
        onDone: vi.fn(),
        onError,
      },
    );
    expect(onError).toHaveBeenCalledWith(
      "Universal chat failed, please try again",
    );
  });
});

describe("tokenizeCitations mid-stream partial markers", () => {
  it("treats incomplete cite markers as plain text", () => {
    const partial = "Demand is real [cite:s";
    const tokens = tokenizeCitations(partial);
    expect(tokens).toEqual([{ type: "text", value: partial }]);
  });

  it("resolves a cite once the closing bracket arrives", () => {
    const complete = "Demand is real [cite:s1].";
    const tokens = tokenizeCitations(complete);
    expect(tokens).toEqual([
      { type: "text", value: "Demand is real " },
      { type: "marker", marker: "[cite:s1]" },
      { type: "text", value: "." },
    ]);
  });

  it("progressive tokenization then finalizes with source_refs payload shape", () => {
    // Mid-stream: partial marker stays text; after full marker, tokenizes.
    let streamed = "Demand is real [cite:s";
    expect(tokenizeCitations(streamed)).toEqual([
      { type: "text", value: streamed },
    ]);
    streamed += "1]";
    expect(tokenizeCitations(streamed)).toEqual([
      { type: "text", value: "Demand is real " },
      { type: "marker", marker: "[cite:s1]" },
    ]);
    // tool_result payload arrives with source_refs — chips resolve by marker_id.
    const sourceRefs = [
      {
        marker_id: "[cite:s1]",
        source_title: "Example",
        source_url: "https://example.com",
        source_domain: "example.com",
      },
    ];
    const tokens = tokenizeCitations(streamed);
    const marker = tokens.find((t) => t.type === "marker");
    expect(marker).toEqual({ type: "marker", marker: "[cite:s1]" });
    expect(
      sourceRefs.find(
        (r) => r.marker_id.toLowerCase() === "[cite:s1]",
      )?.source_domain,
    ).toBe("example.com");
  });
});
