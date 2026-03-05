export const hasScoreChanged = (
  prevScoreA: number,
  prevScoreB: number,
  nextScoreA: number,
  nextScoreB: number
): boolean => prevScoreA !== nextScoreA || prevScoreB !== nextScoreB;
