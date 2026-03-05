package com.scoreboard.android

object ScoreStateCodec {
  fun encode(state: ScoreState): String {
    return listOf(
      state.teamA,
      state.teamB,
      state.scoreA.toString(),
      state.scoreB.toString(),
      state.round.toString()
    ).joinToString("|")
  }

  fun decode(raw: String?): ScoreState? {
    if (raw.isNullOrBlank()) return null
    val parts = raw.split("|")
    if (parts.size != 5) return null
    val scoreA = parts[2].toIntOrNull() ?: return null
    val scoreB = parts[3].toIntOrNull() ?: return null
    val round = parts[4].toIntOrNull() ?: return null
    return ScoreState(parts[0], parts[1], scoreA, scoreB, round)
  }
}
