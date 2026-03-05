package com.scoreboard.android

import org.junit.Assert.assertEquals
import org.junit.Test

class ScoreStateTest {
  @Test
  fun nextIncrementsRound() {
    val state = ScoreState("A", "B", 0, 0, 1)
    val next = state.next(seed = 2L)
    assertEquals(2, next.round)
  }

  @Test
  fun nextIncrementsScoresDeterministically() {
    val state = ScoreState("A", "B", 0, 0, 1)
    val next = state.next(seed = 6L)
    assertEquals(1, next.scoreA)
    assertEquals(1, next.scoreB)
  }
}
