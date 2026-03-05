import type { VercelRequest, VercelResponse } from "@vercel/node";
import { removeSubscription } from "../server/db.js";
import { readJsonBody } from "../server/http.js";
import { unfollowRequestSchema } from "../server/validators.js";

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  if (req.method !== "POST") {
    res.status(405).json({ ok: false, error: "Method not allowed" });
    return;
  }

  try {
    const body = await readJsonBody(req);
    const parsed = unfollowRequestSchema.safeParse(body);
    if (!parsed.success) {
      res.status(400).json({ ok: false, error: "Invalid request" });
      return;
    }

    const { matchId, deviceToken } = parsed.data;
    await removeSubscription(matchId, deviceToken);
    res.status(200).json({ ok: true });
  } catch (error) {
    res
      .status(500)
      .json({ ok: false, error: (error as Error).message });
  }
}
