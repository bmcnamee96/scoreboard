import "dotenv/config";

const DEFAULT_URL = "http://localhost:3000/api/cron/poll";
const DEFAULT_INTERVAL_MS = 60_000;

const pollUrl = process.env.POLL_URL ?? DEFAULT_URL;
const intervalMs = Number.parseInt(
  process.env.POLL_INTERVAL_MS ?? String(DEFAULT_INTERVAL_MS),
  10
);

const runPoll = async (): Promise<void> => {
  try {
    const response = await fetch(pollUrl, { method: "GET" });
    const text = await response.text();
    const ok = response.ok ? "ok" : `status ${response.status}`;
    console.log(`[poll] ${ok} ${text}`);
  } catch (error) {
    console.error(`[poll] error ${(error as Error).message}`);
  }
};

console.log(`[poll] target=${pollUrl} intervalMs=${intervalMs}`);
runPoll();
setInterval(runPoll, intervalMs);
