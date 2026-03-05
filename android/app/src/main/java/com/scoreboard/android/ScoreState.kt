package com.scoreboard.android

data class ScoreState(
  val teamA: String,
  val teamB: String,
  val scoreA: Int,
  val scoreB: Int,
  val round: Int
) {
  fun next(seed: Long = System.currentTimeMillis()): ScoreState {
    val aInc = if (seed % 2L == 0L) 1 else 0
    val bInc = if (seed % 3L == 0L) 1 else 0
    return copy(
      scoreA = scoreA + aInc,
      scoreB = scoreB + bInc,
      round = round + 1
    )
  }

  fun title(): String = "$teamA vs $teamB"

  fun body(): String = "$scoreA-$scoreB · Round $round"
}
