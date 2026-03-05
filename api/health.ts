import type { VercelRequest, VercelResponse } from "@vercel/node";
import { ensureSchema } from "../server/db.js";

export default async function handler(
  _req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  try {
    await ensureSchema();
    res.status(200).json({ ok: true });
  } catch (error) {
    res.status(500).json({ ok: false, error: (error as Error).message });
  }
}
