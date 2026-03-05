import type { VercelRequest } from "@vercel/node";

export const readJsonBody = async <T>(
  req: VercelRequest
): Promise<T | null> => {
  if (req.body) {
    return req.body as T;
  }

  return new Promise((resolve) => {
    let raw = "";
    req.on("data", (chunk) => {
      raw += String(chunk);
    });
    req.on("end", () => {
      try {
        resolve(JSON.parse(raw) as T);
      } catch {
        resolve(null);
      }
    });
  });
};
