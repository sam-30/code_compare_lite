import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App, {
  scoreColor, scoreBg, scoreBar,
  Pct, MiniBar,
  CallGraphViz, SharedPills, FilePairDetail, MethodCard,
} from "./App";

// ── score helpers ─────────────────────────────────────────────────────────────

describe("scoreColor", () => {
  it("returns red class for high scores", () => {
    expect(scoreColor(0.9)).toContain("red");
  });
  it("returns yellow class for mid scores", () => {
    expect(scoreColor(0.5)).toContain("yellow");
  });
  it("returns green class for low scores", () => {
    expect(scoreColor(0.1)).toContain("green");
  });
  it("threshold at 0.7 is red", () => {
    expect(scoreColor(0.7)).toContain("red");
  });
  it("threshold at 0.4 is yellow", () => {
    expect(scoreColor(0.4)).toContain("yellow");
  });
});

describe("scoreBg", () => {
  it("returns red bg for high scores", () => {
    expect(scoreBg(0.9)).toContain("red");
  });
  it("returns yellow bg for mid scores", () => {
    expect(scoreBg(0.5)).toContain("yellow");
  });
  it("returns green bg for low scores", () => {
    expect(scoreBg(0.2)).toContain("green");
  });
});

describe("scoreBar", () => {
  it("returns red bar for high scores", () => {
    expect(scoreBar(0.9)).toContain("red");
  });
  it("returns yellow bar for mid scores", () => {
    expect(scoreBar(0.55)).toContain("yellow");
  });
  it("returns green bar for low scores", () => {
    expect(scoreBar(0.1)).toContain("green");
  });
});

// ── Pct ───────────────────────────────────────────────────────────────────────

describe("Pct", () => {
  it("formats score as percentage with one decimal", () => {
    render(<Pct score={0.756} />);
    expect(screen.getByText("75.6%")).toBeInTheDocument();
  });
  it("shows 0.0% for score 0", () => {
    render(<Pct score={0} />);
    expect(screen.getByText("0.0%")).toBeInTheDocument();
  });
  it("shows 100.0% for score 1", () => {
    render(<Pct score={1} />);
    expect(screen.getByText("100.0%")).toBeInTheDocument();
  });
  it("applies red color class for high score", () => {
    const { container } = render(<Pct score={0.9} />);
    expect(container.firstChild).toHaveClass("text-red-600");
  });
  it("applies green color class for low score", () => {
    const { container } = render(<Pct score={0.1} />);
    expect(container.firstChild).toHaveClass("text-green-600");
  });
});

// ── MiniBar ───────────────────────────────────────────────────────────────────

describe("MiniBar", () => {
  it("renders a percentage label", () => {
    render(<MiniBar score={0.5} />);
    expect(screen.getByText("50.0%")).toBeInTheDocument();
  });
  it("renders bar with correct width style", () => {
    const { container } = render(<MiniBar score={0.6} />);
    const bar = container.querySelector("[style]");
    expect(bar).toHaveStyle({ width: "60%" });
  });
});

// ── SharedPills ───────────────────────────────────────────────────────────────

describe("SharedPills", () => {
  it("renders all items when count ≤ 24", () => {
    const items = ["alpha", "beta", "gamma"];
    render(<SharedPills label="Test" items={items} colorClass="bg-gray-100" />);
    items.forEach(i => expect(screen.getByText(i)).toBeInTheDocument());
  });

  it("shows only 24 items when count > 24", () => {
    const items = Array.from({ length: 30 }, (_, i) => `item${i}`);
    render(<SharedPills label="Test" items={items} colorClass="bg-gray-100" />);
    expect(screen.queryByText("item29")).not.toBeInTheDocument();
    expect(screen.getByText("+6 more")).toBeInTheDocument();
  });

  it("shows all items after clicking show-more", async () => {
    const user = userEvent.setup();
    const items = Array.from({ length: 30 }, (_, i) => `item${i}`);
    render(<SharedPills label="Test" items={items} colorClass="bg-gray-100" />);
    await user.click(screen.getByText("+6 more"));
    expect(screen.getByText("item29")).toBeInTheDocument();
  });

  it("renders label", () => {
    render(<SharedPills label="My Label" items={["x"]} colorClass="" />);
    expect(screen.getByText("My Label")).toBeInTheDocument();
  });
});

// ── FilePairDetail ────────────────────────────────────────────────────────────

const BASIC_FM = {
  file_a_path: "src/foo.py",
  file_b_path: "lib/bar.py",
  similarity_score: 0.75,
  method_id: "line_similarity",
  detail: {},
};

describe("FilePairDetail", () => {
  it("renders file paths", () => {
    render(<FilePairDetail fm={BASIC_FM} />);
    expect(screen.getByText("src/foo.py")).toBeInTheDocument();
    expect(screen.getByText("lib/bar.py")).toBeInTheDocument();
  });

  it("renders similarity score", () => {
    render(<FilePairDetail fm={BASIC_FM} />);
    expect(screen.getByText("75.0%")).toBeInTheDocument();
  });

  it("shows expand button when detail has content", () => {
    const fm = { ...BASIC_FM, detail: { some_key: "some_value" } };
    render(<FilePairDetail fm={fm} />);
    expect(screen.getByText("code")).toBeInTheDocument();
  });

  it("expands to show shared functions", async () => {
    const user = userEvent.setup();
    const fm = { ...BASIC_FM, detail: { shared_functions: ["doThing", "compute"] } };
    render(<FilePairDetail fm={fm} />);
    await user.click(screen.getByText("code"));
    expect(screen.getByText("doThing")).toBeInTheDocument();
    expect(screen.getByText("compute")).toBeInTheDocument();
  });

  it("collapses when expand button clicked again", async () => {
    const user = userEvent.setup();
    const fm = { ...BASIC_FM, detail: { shared_functions: ["doThing"] } };
    render(<FilePairDetail fm={fm} />);
    await user.click(screen.getByText("code"));
    expect(screen.getByText("doThing")).toBeInTheDocument();
    await user.click(screen.getByText("hide"));
    expect(screen.queryByText("doThing")).not.toBeInTheDocument();
  });
});

// ── MethodCard ────────────────────────────────────────────────────────────────

const BASE_METHOD = {
  method_id: "file_hash",
  score: 0.5,
  weight: 0.15,
  duration_ms: 42,
  details: {},
};

describe("MethodCard", () => {
  it("renders method name", () => {
    render(<MethodCard method={BASE_METHOD} matches={[]} nameA="A" nameB="B" />);
    expect(screen.getByText("Exact File Hash")).toBeInTheDocument();
  });

  it("renders score bar", () => {
    render(<MethodCard method={BASE_METHOD} matches={[]} nameA="A" nameB="B" />);
    expect(screen.getByText("50.0%")).toBeInTheDocument();
  });

  it("renders weight and duration", () => {
    render(<MethodCard method={BASE_METHOD} matches={[]} nameA="A" nameB="B" />);
    expect(screen.getByText("15% weight")).toBeInTheDocument();
    expect(screen.getByText("42ms")).toBeInTheDocument();
  });

  it("shows error badge when details has error", () => {
    const method = { ...BASE_METHOD, details: { error: "something broke" } };
    render(<MethodCard method={method} matches={[]} nameA="A" nameB="B" />);
    expect(screen.getByText("⚠ error")).toBeInTheDocument();
  });

  it("expands to show error message on click", async () => {
    const user = userEvent.setup();
    const method = { ...BASE_METHOD, details: { error: "something broke" } };
    render(<MethodCard method={method} matches={[]} nameA="A" nameB="B" />);
    await user.click(screen.getByText("Exact File Hash"));
    expect(screen.getByText(/something broke/)).toBeInTheDocument();
  });

  it("shows file pair count badge", () => {
    const matches = [{ ...BASIC_FM }];
    render(<MethodCard method={BASE_METHOD} matches={matches} nameA="A" nameB="B" />);
    expect(screen.getByText("1 file pair")).toBeInTheDocument();
  });

  it("shows plural file pairs", () => {
    const matches = [BASIC_FM, { ...BASIC_FM, file_b_path: "other.py" }];
    render(<MethodCard method={BASE_METHOD} matches={matches} nameA="A" nameB="B" />);
    expect(screen.getByText("2 file pairs")).toBeInTheDocument();
  });
});

// ── CallGraphViz ───────────────────────────────────────────────────────────────

const GRAPH_DATA = {
  nodes: [
    { id: "funcA", group: "a" as const },
    { id: "funcB", group: "b" as const },
    { id: "shared", group: "shared" as const },
  ],
  edges: [
    { source: "funcA", target: "shared", repo: "a" as const },
    { source: "funcB", target: "shared", repo: "b" as const },
  ],
};

describe("CallGraphViz", () => {
  it("renders an SVG element", () => {
    const { container } = render(
      <CallGraphViz graph={GRAPH_DATA} nameA="RepoA" nameB="RepoB" />
    );
    expect(container.querySelector("svg")).toBeInTheDocument();
  });

  it("renders one circle per node", () => {
    const { container } = render(
      <CallGraphViz graph={GRAPH_DATA} nameA="RepoA" nameB="RepoB" />
    );
    const circles = container.querySelectorAll("circle");
    expect(circles).toHaveLength(GRAPH_DATA.nodes.length);
  });

  it("renders column headers with node counts", () => {
    render(<CallGraphViz graph={GRAPH_DATA} nameA="RepoA" nameB="RepoB" />);
    expect(screen.getByText(/RepoA.*only.*\(1\)/)).toBeInTheDocument();
    expect(screen.getByText(/Shared.*\(1\)/)).toBeInTheDocument();
    expect(screen.getByText(/RepoB.*only.*\(1\)/)).toBeInTheDocument();
  });

  it("renders legend items", () => {
    render(<CallGraphViz graph={GRAPH_DATA} nameA="RepoA" nameB="RepoB" />);
    expect(screen.getByText("RepoA only")).toBeInTheDocument();
    expect(screen.getByText("Shared")).toBeInTheDocument();
    expect(screen.getByText("RepoB only")).toBeInTheDocument();
  });

  it("renders edges as lines or paths", () => {
    const { container } = render(
      <CallGraphViz graph={GRAPH_DATA} nameA="RepoA" nameB="RepoB" />
    );
    const edgeEls = container.querySelectorAll("line, path[stroke]");
    // At least the edges should be rendered (not counting defs/markers)
    expect(edgeEls.length).toBeGreaterThan(0);
  });

  it("renders node labels as text elements", () => {
    const { container } = render(
      <CallGraphViz graph={GRAPH_DATA} nameA="RepoA" nameB="RepoB" />
    );
    const textEls = Array.from(container.querySelectorAll("text"));
    const labels = textEls.map(t => t.textContent ?? "");
    expect(labels).toContain("funcA");
    expect(labels).toContain("funcB");
    expect(labels).toContain("shared");
  });

  it("truncates long node names", () => {
    const longGraph = {
      nodes: [{ id: "a".repeat(30), group: "a" as const }],
      edges: [],
    };
    render(<CallGraphViz graph={longGraph} nameA="A" nameB="B" />);
    // Label should be truncated (≤ LABEL_MAX chars + ellipsis)
    const textEls = Array.from(document.querySelectorAll("text"));
    const labelText = textEls.find(t => t.textContent?.includes("…"))?.textContent ?? "";
    expect(labelText.length).toBeLessThan(30);
  });

  it("handles empty graph gracefully", () => {
    const { container } = render(
      <CallGraphViz graph={{ nodes: [], edges: [] }} nameA="A" nameB="B" />
    );
    expect(container.querySelectorAll("circle")).toHaveLength(0);
  });
});

// ── App smoke tests ───────────────────────────────────────────────────────────

describe("App", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("renders the page title", () => {
    render(<App />);
    expect(screen.getByText("Code Compare")).toBeInTheDocument();
  });

  it("renders both repo cards", () => {
    render(<App />);
    expect(screen.getByText("Repo A — Reference")).toBeInTheDocument();
    expect(screen.getByText("Repo B — Suspect")).toBeInTheDocument();
  });

  it("renders Run Comparison button", () => {
    render(<App />);
    expect(screen.getByRole("button", { name: /run comparison/i })).toBeInTheDocument();
  });

  it("shows spinner after submission", async () => {
    const user = userEvent.setup();
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ job_id: "abc123" }),
    });
    render(<App />);
    await user.click(screen.getByRole("button", { name: /run comparison/i }));
    await waitFor(() => {
      expect(screen.getByText(/analyzing repositories/i)).toBeInTheDocument();
    });
  });

  it("shows error message on failed submission", async () => {
    const user = userEvent.setup();
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: "Bad request" }),
    });
    render(<App />);
    await user.click(screen.getByRole("button", { name: /run comparison/i }));
    await waitFor(() => {
      expect(screen.getByText(/bad request/i)).toBeInTheDocument();
    });
  });

  it("each repo card has source type tab buttons", () => {
    render(<App />);
    // Each of the 2 cards has 3 tab buttons (Git URL, Local Path, Upload ZIP)
    const localButtons = screen.getAllByRole("button", { name: /local path/i });
    expect(localButtons.length).toBe(2);
    const zipButtons = screen.getAllByRole("button", { name: /upload zip/i });
    expect(zipButtons.length).toBe(2);
  });
});
