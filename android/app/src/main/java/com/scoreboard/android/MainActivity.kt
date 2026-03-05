package com.scoreboard.android

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

class MainActivity : AppCompatActivity() {
  private lateinit var statusView: TextView

  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    setContentView(R.layout.activity_main)

    statusView = findViewById(R.id.statusText)
    val startButton: Button = findViewById(R.id.startButton)
    val updateButton: Button = findViewById(R.id.updateButton)
    val stopButton: Button = findViewById(R.id.stopButton)

    startButton.setOnClickListener {
      ensureNotifications()
      ContextCompat.startForegroundService(this, LiveScoreService.startIntent(this))
      statusView.text = getString(R.string.status_running)
    }

    updateButton.setOnClickListener {
      ContextCompat.startForegroundService(this, LiveScoreService.updateIntent(this))
      statusView.text = getString(R.string.status_updated)
    }

    stopButton.setOnClickListener {
      ContextCompat.startForegroundService(this, LiveScoreService.stopIntent(this))
      statusView.text = getString(R.string.status_stopped)
    }

    statusView.text = getString(R.string.status_idle)
  }

  private fun ensureNotifications() {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
    if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) ==
      PackageManager.PERMISSION_GRANTED) return
    ActivityCompat.requestPermissions(
      this,
      arrayOf(Manifest.permission.POST_NOTIFICATIONS),
      NOTIFICATION_REQUEST_CODE
    )
  }

  companion object {
    private const val NOTIFICATION_REQUEST_CODE = 7001
  }
}
