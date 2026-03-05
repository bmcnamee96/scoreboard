package com.scoreboard.android

import android.content.Context

object WidgetStateStorage {
  private const val PREFS_NAME = "scoreboard_widget_prefs"
  private const val KEY_STATE = "score_state"

  fun save(context: Context, state: ScoreState) {
    val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    prefs.edit().putString(KEY_STATE, ScoreStateCodec.encode(state)).apply()
  }

  fun load(context: Context): ScoreState? {
    val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    return ScoreStateCodec.decode(prefs.getString(KEY_STATE, null))
  }
}
