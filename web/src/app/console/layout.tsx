import type { ReactNode } from "react";
import { ConsoleSessionProvider } from "./session";
import { ConsoleNav } from "./nav";

export const metadata = { title: "Console | Agoda Voice" };

export default function ConsoleLayout({ children }: { children: ReactNode }) {
  return (
    <ConsoleSessionProvider>
      <div className="mx-auto max-w-page px-6 py-8">
        <ConsoleNav />
        <div className="mt-6">{children}</div>
      </div>
    </ConsoleSessionProvider>
  );
}
