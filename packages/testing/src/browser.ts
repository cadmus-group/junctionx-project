import { setupWorker, type SetupWorker } from "msw/browser";
import { handlers } from "./handlers";

let worker: SetupWorker | null = null;

export function getWorker(): SetupWorker {
  if (!worker) worker = setupWorker(...handlers);
  return worker;
}

export interface StartMswOptions {
  serviceWorkerUrl?: string;
  quiet?: boolean;
}

/** Start the MSW browser worker for demo mode. Safe to call once on the client. */
export async function startMsw(options: StartMswOptions = {}): Promise<void> {
  if (typeof window === "undefined") return;
  const w = getWorker();
  await w.start({
    serviceWorker: { url: options.serviceWorkerUrl ?? "/mockServiceWorker.js" },
    onUnhandledRequest: "bypass",
    quiet: options.quiet ?? true,
  });
}
