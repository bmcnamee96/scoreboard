package com.scoreboard.android

import android.appwidget.AppWidgetManager
import android.content.ComponentName
import android.content.Context
import android.widget.RemoteViews

object WidgetUpdater {
  fun updateAll(context: Context, state: ScoreState) {
    val manager = AppWidgetManager.getInstance(context)
    val ids = manager.getAppWidgetIds(ComponentName(context, ScoreWidgetProvider::class.java))
    update(context, manager, ids, state)
  }

  fun update(
    context: Context,
    manager: AppWidgetManager,
    appWidgetIds: IntArray,
    state: ScoreState
  ) {
    for (id in appWidgetIds) {
      val views = RemoteViews(context.packageName, R.layout.widget_score)
      views.setTextViewText(R.id.widgetTitle, state.title())
      views.setTextViewText(R.id.widgetScore, "${state.scoreA}-${state.scoreB}")
      views.setTextViewText(R.id.widgetRound, "Round ${state.round}")
      manager.updateAppWidget(id, views)
    }
  }
}
