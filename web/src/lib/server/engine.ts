// The site's one connection to the engine. Server-only: route handlers in app/api/* call it,
// so browser code never holds an engine token or the demo passcode.
// One interface, two implementations, chosen once from AV_API_MODE (http | mock). No fallback.
import { MockBackend, UnknownTokenError } from "@/lib/mock-backend";
import { can, type Action, type Role } from "@/lib/rbac";
import type { DemoRun, KillSwitchResult, ScenarioId } from "@/lib/demo-types";
import type { StatusReport } from "@/lib/console-types";
import { askMock, type ConciergeAnswer } from "./concierge-mock";
import { RECORDED_RUNS } from "./recorded-runs";

export interface EngineResponse {
  status: number;
  body: unknown;
}

export interface BookingRequest {
  session_id: string;
  name: string;
  email: string;
  company: string;
  slot: string;
  consent: true;
}

export interface Engine {
  readonly mode: "http" | "mock";
  console(method: string, path: string, token: string, body: unknown): Promise<EngineResponse>;
  demoRun(scenario: ScenarioId, passcode: string): Promise<DemoRun>;
  demoKill(passcode: string): Promise<KillSwitchResult>;
  ask(sessionId: string, message: string): Promise<ConciergeAnswer>;
  slots(): Promise<{ slots: string[] }>;
  book(req: BookingRequest): Promise<{ booking_id: string; slot: string }>;
  status(): Promise<StatusReport>;
}

export class EngineError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "EngineError";
  }
}

class HttpEngine implements Engine {
  readonly mode = "http" as const;
  constructor(private readonly base: string) {}

  private async call(method: string, path: string, headers: Record<string, string>, body?: unknown): Promise<EngineResponse> {
    const res = await fetch(`${this.base}${path}`, {
      method,
      headers: { ...headers, "content-type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
    });
    const text = await res.text();
    return { status: res.status, body: text ? (JSON.parse(text) as unknown) : null };
  }

  private async ok<T>(r: Promise<EngineResponse>): Promise<T> {
    const res = await r;
    if (res.status >= 400) throw new EngineError(res.status, `engine returned ${res.status}`);
    return res.body as T;
  }

  console(method: string, path: string, token: string, body: unknown): Promise<EngineResponse> {
    return this.call(method, path, { authorization: `Bearer ${token}` }, method === "GET" ? undefined : body);
  }

  demoRun(scenario: ScenarioId, passcode: string): Promise<DemoRun> {
    return this.ok(this.call("POST", "/demo/run", { "x-demo-passcode": passcode }, { scenario }));
  }

  demoKill(passcode: string): Promise<KillSwitchResult> {
    return this.ok(this.call("POST", "/demo/killswitch", { "x-demo-passcode": passcode }, {}));
  }

  ask(sessionId: string, message: string): Promise<ConciergeAnswer> {
    return this.ok(this.call("POST", "/concierge/ask", {}, { session_id: sessionId, message }));
  }

  slots(): Promise<{ slots: string[] }> {
    return this.ok(this.call("GET", "/concierge/slots", {}));
  }

  book(req: BookingRequest): Promise<{ booking_id: string; slot: string }> {
    return this.ok(this.call("POST", "/concierge/book", {}, req));
  }

  status(): Promise<StatusReport> {
    return this.ok(this.call("GET", "/status", {}));
  }
}

function json(status: number, body: unknown): EngineResponse {
  return { status, body };
}

const NEEDS: Record<string, Action> = {
  "GET /campaigns": "view_console",
  "GET /calls": "view_calls",
  "GET /handoff": "view_calls",
  "GET /numbers": "view_console",
  "GET /costs": "view_costs",
  "GET /audit": "view_audit",
  "GET /killswitch": "view_console",
  "POST /killswitch": "operate_kill_switch",
};

class MockEngine implements Engine {
  readonly mode = "mock" as const;
  private readonly backend = new MockBackend();

  async console(method: string, path: string, token: string, body: unknown): Promise<EngineResponse> {
    let role: Role;
    let actor: string;
    try {
      ({ role, actor } = this.backend.identify(token));
    } catch (e) {
      if (e instanceof UnknownTokenError) return json(401, { error: "auth_error", detail: "unknown token" });
      throw e;
    }
    const [route, query = ""] = path.split("?");
    if (method === "GET" && route === "/whoami") return json(200, { actor, role });
    const need = NEEDS[`${method} ${route}`];
    if (!need) return json(404, { error: "http_404", detail: `no mock for ${method} ${route}` });
    if (!can(role, need)) return json(403, { error: "forbidden", detail: `role ${role} may not ${need}` });
    switch (`${method} ${route}`) {
      case "GET /campaigns":
        return json(200, this.backend.campaigns);
      case "GET /calls":
        return json(200, new URLSearchParams(query).get("state") === "live" ? this.backend.liveCalls() : this.backend.outcomes);
      case "GET /handoff":
        return json(200, this.backend.handoffs);
      case "GET /numbers":
        return json(200, this.backend.numbers);
      case "GET /costs":
        return json(200, this.backend.costs);
      case "GET /audit":
        return json(200, this.backend.audit());
      case "GET /killswitch":
        return json(200, this.backend.killSwitch());
      case "POST /killswitch": {
        const b = body as { engaged?: unknown; reason?: unknown };
        if (typeof b.engaged !== "boolean" || typeof b.reason !== "string" || b.reason.trim().length < 3)
          return json(422, { error: "validation_error", detail: "engaged (bool) and reason (3+ chars) are required" });
        return json(200, this.backend.setKillSwitch({ actor, role }, b.engaged, b.reason));
      }
    }
    return json(404, { error: "http_404", detail: "unreachable" });
  }

  // The mock replays runs recorded from the engine (web/scripts/record_demo.py).
  async demoRun(scenario: ScenarioId): Promise<DemoRun> {
    return RECORDED_RUNS[scenario];
  }

  // The mock has no dispatcher to stop; the demo page measures its own round trip.
  async demoKill(): Promise<KillSwitchResult> {
    return { engaged: true, stopped_in_ms: 0 };
  }

  async ask(_sessionId: string, message: string): Promise<ConciergeAnswer> {
    return askMock(message);
  }

  async slots(): Promise<{ slots: string[] }> {
    // Next three weekdays at 11:00 and 16:00 IST.
    const out: string[] = [];
    const d = new Date();
    while (out.length < 6) {
      d.setUTCDate(d.getUTCDate() + 1);
      const day = d.getUTCDay();
      if (day === 0 || day === 6) continue;
      for (const hhmm of ["05:30", "10:30"]) out.push(`${d.toISOString().slice(0, 10)}T${hhmm}:00Z`);
    }
    return { slots: out };
  }

  async book(req: BookingRequest): Promise<{ booking_id: string; slot: string }> {
    return { booking_id: `mock-booking-${req.session_id.slice(0, 8)}`, slot: req.slot };
  }

  async status(): Promise<StatusReport> {
    const now = new Date().toISOString();
    return {
      overall: "operational",
      components: [
        { name: "Mock engine (no live service)", status: "operational", checked_at: now },
      ],
      history: [],
    };
  }
}

let engine: Engine | null = null;

export function getEngine(): Engine {
  if (engine) return engine;
  const mode = process.env.AV_API_MODE ?? "mock";
  if (mode === "mock") engine = new MockEngine();
  else if (mode === "http") {
    const base = process.env.AV_API_URL;
    if (!base) throw new Error("AV_API_URL is required when AV_API_MODE=http");
    engine = new HttpEngine(base);
  } else throw new Error(`AV_API_MODE must be http or mock, got ${mode}`);
  return engine;
}
