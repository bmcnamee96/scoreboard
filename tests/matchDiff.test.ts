import { describe, expect, it } from "vitest";
import { hasScoreChanged } from "../server/matchDiff";

describe("hasScoreChanged", () => {
  it("returns true when either score changes", () => {
    expect(hasScoreChanged(1, 2, 2, 2)).toBe(true);
    expect(hasScoreChanged(1, 2, 1, 3)).toBe(true);
  });

  it("returns false when scores are identical", () => {
    expect(hasScoreChanged(5, 5, 5, 5)).toBe(false);
  });
});
