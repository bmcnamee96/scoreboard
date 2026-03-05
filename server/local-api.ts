import http from "node:http";
import { URL } from "node:url";
import type { VercelRequest, VercelResponse } from "@vercel/node";
import "dotenv/config";

import health from "../api/health.js";
import matches from "../api/matches.js";
import follow from "../api/follow.js";
import unfollow from "../api/unfollow.js";
import poll from "../api/cron/poll.js";

type Handler = (req: VercelRequest, res: VercelResponse) => Promise<void> | void;

const routes: Record<string, Handler> = {
  "/api/health": health,
  "/api/matches": matches,
  "/api/follow": follow,
  "/api/unfollow": unfollow,
  "/api/cron/poll": poll
};

const withVercelResponse = (res: http.ServerResponse): VercelResponse => {
  const vercelRes = res as VercelResponse;
  vercelRes.status = (code: number) => {
    res.statusCode = code;
    return vercelRes;
  };
  vercelRes.json = (data: unknown) => {
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.end(JSON.stringify(data));
    return vercelRes;
  };
  vercelRes.send = (data: unknown) => {
    if (typeof data === "string" || Buffer.isBuffer(data)) {
      res.end(data);
      return vercelRes;
    }
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.end(JSON.stringify(data));
    return vercelRes;
  };
  return vercelRes;
};

const server = http.createServer(async (req, res) => {
  const requestUrl = new URL(req.url ?? "/", `http://${req.headers.host}`);
  const handler = routes[requestUrl.pathname];

  (req as VercelRequest).query = Object.fromEntries(
    requestUrl.searchParams.entries()
  );

  if (!handler) {
    res.statusCode = 404;
    res.end("Not Found");
    return;
  }

  try {
    await handler(req as VercelRequest, withVercelResponse(res));
  } catch (error) {
    res.statusCode = 500;
    res.end((error as Error).message);
  }
});

server.listen(3000, () => {
  // Local API for dev without Vercel routing.
  console.log("Local API server running on http://localhost:3000");
});
