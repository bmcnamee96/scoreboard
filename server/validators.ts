import { z } from "zod";

export const followRequestSchema = z.object({
  matchId: z.string().min(1),
  deviceToken: z.string().min(1)
});

export const unfollowRequestSchema = z.object({
  matchId: z.string().min(1),
  deviceToken: z.string().min(1)
});

export const debugPushSchema = z
  .object({
    matchId: z.string().min(1).optional(),
    deviceToken: z.string().min(1).optional()
  })
  .refine((value) => value.matchId || value.deviceToken, {
    message: "matchId or deviceToken required"
  });
