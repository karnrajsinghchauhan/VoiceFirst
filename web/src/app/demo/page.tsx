// The private live demo (S10). The middleware has already checked the passcode cookie.
import { DemoApp } from "@/components/demo/demo-app";

export const metadata = { title: "Live demo | Agoda Voice", robots: { index: false, follow: false } };
export const dynamic = "force-dynamic";

export default function DemoPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="font-display text-3xl">Live demo</h1>
      <p className="mt-2 max-w-3xl text-sm text-muted">
        Each call runs the real engine: holdout, every compliance gate, a single-use clearance, the agent and its tools,
        then post-call. Providers are mocks and the customer is a scripted persona, so no real call or message is sent. The demo models a contact-centre queue with a person free; the connection to a real contact centre is not built yet (AV-CCAAS-1), and no real phone call has been made (0 of 20 test calls).
        Names, bookings and amounts are synthetic.
      </p>
      <DemoApp />
      <p className="mt-10 text-xs text-muted">
        Agoda Voice is an independent ProsperOps product and is not affiliated with or endorsed by Agoda.
      </p>
    </div>
  );
}
