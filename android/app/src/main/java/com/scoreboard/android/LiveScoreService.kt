package com.scoreboard.android

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.text.SpannableString
import android.text.Spanned
import android.text.style.StyleSpan
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat

class LiveScoreService : Service() {
  private val handler = Handler(Looper.getMainLooper())
  private var running = false
  private var state = ScoreState("Alpha", "Bravo", 0, 0, 1)

  override fun onBind(intent: Intent?): IBinder? = null

  override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
    when (intent?.action) {
      ACTION_START -> start()
      ACTION_STOP -> stop()
      ACTION_UPDATE -> updateOnce()
    }
    return START_STICKY
  }

  private fun start() {
    if (running) return
    running = true
    createChannel()
    startForeground(NOTIFICATION_ID, buildNotification())
    WidgetStateStorage.save(this, state)
    WidgetUpdater.updateAll(this, state)
    scheduleNext()
  }

  private fun stop() {
    running = false
    handler.removeCallbacksAndMessages(null)
    stopForeground(STOP_FOREGROUND_REMOVE)
    stopSelf()
  }

  private fun updateOnce() {
    if (!running) return
    state = state.next()
    NotificationManagerCompat.from(this).notify(NOTIFICATION_ID, buildNotification())
    WidgetStateStorage.save(this, state)
    WidgetUpdater.updateAll(this, state)
  }

  private fun scheduleNext() {
    if (!running) return
    handler.postDelayed(
      {
        updateOnce()
        scheduleNext()
      },
      UPDATE_INTERVAL_MS
    )
  }

  private fun buildNotification(): Notification {
    val title = SpannableString(state.title()).apply {
      setSpan(StyleSpan(android.graphics.Typeface.BOLD), 0, length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
    }
    val scoreLine = SpannableString("${state.scoreA}-${state.scoreB}").apply {
      setSpan(StyleSpan(android.graphics.Typeface.BOLD), 0, length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
    }
    val roundLine = "Round ${state.round}"
    val bigText = "${state.teamA} vs ${state.teamB}\n${state.scoreA}-${state.scoreB}\n$roundLine"

    return NotificationCompat.Builder(this, CHANNEL_ID)
      .setContentTitle(title)
      .setContentText(state.body())
      .setStyle(NotificationCompat.BigTextStyle().bigText(bigText))
      .setSubText(roundLine)
      .setContentInfo("${state.scoreA}-${state.scoreB}")
      .setSmallIcon(android.R.drawable.ic_popup_sync)
      .setOnlyAlertOnce(true)
      .setOngoing(true)
      .setSilent(true)
      .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
      .setPriority(NotificationCompat.PRIORITY_HIGH)
      .build()
  }

  private fun createChannel() {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
    val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
    val channel = NotificationChannel(
      CHANNEL_ID,
      "Live Score Updates",
      NotificationManager.IMPORTANCE_HIGH
    )
    channel.lockscreenVisibility = Notification.VISIBILITY_PUBLIC
    manager.createNotificationChannel(channel)
  }

  companion object {
    private const val CHANNEL_ID = "scoreboard_live_score"
    private const val NOTIFICATION_ID = 4221
    private const val UPDATE_INTERVAL_MS = 30_000L

    private const val ACTION_START = "com.scoreboard.android.START"
    private const val ACTION_STOP = "com.scoreboard.android.STOP"
    private const val ACTION_UPDATE = "com.scoreboard.android.UPDATE"

    fun startIntent(context: Context): Intent =
      Intent(context, LiveScoreService::class.java).setAction(ACTION_START)

    fun stopIntent(context: Context): Intent =
      Intent(context, LiveScoreService::class.java).setAction(ACTION_STOP)

    fun updateIntent(context: Context): Intent =
      Intent(context, LiveScoreService::class.java).setAction(ACTION_UPDATE)
  }
}
