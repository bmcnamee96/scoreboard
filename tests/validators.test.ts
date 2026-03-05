import { describe, expect, it } from "vitest";
import {
  followRequestSchema,
  unfollowRequestSchema
} from "../server/validators";

describe("followRequestSchema", () => {
  it("accepts a valid payload", () => {
    const result = followRequestSchema.safeParse({
      matchId: "123",
      deviceToken: "token"
    });
    expect(result.success).toBe(true);
  });

  it("rejects an invalid payload", () => {
    const result = followRequestSchema.safeParse({
      matchId: "",
      deviceToken: ""
    });
    expect(result.success).toBe(false);
  });
});

describe("unfollowRequestSchema", () => {
  it("accepts a valid payload", () => {
    const result = unfollowRequestSchema.safeParse({
      matchId: "456",
      deviceToken: "token"
    });
    expect(result.success).toBe(true);
  });
});
