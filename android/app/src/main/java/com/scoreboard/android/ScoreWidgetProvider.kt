package com.scoreboard.android

import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context

class ScoreWidgetProvider : AppWidgetProvider() {
  override fun onUpdate(
    context: Context,
    appWidgetManager: AppWidgetManager,
    appWidgetIds: IntArray
  ) {
    val state = WidgetStateStorage.load(context) ?: ScoreState("Alpha", "Bravo", 0, 0, 1)
    WidgetUpdater.update(context, appWidgetManager, appWidgetIds, state)
  }
}
