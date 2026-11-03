#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动给 APlayer 打"定时关闭记忆"补丁：
1. SleepTimer.kt: 开启定时时记住时长，取消时清除记忆
2. MusicService.kt: App启动/服务创建时自动恢复上次的定时
"""
import os
import sys
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def replace_or_fail(filepath, old_anchor, new_block, file_desc):
    full_path = os.path.join(ROOT, filepath)
    if not os.path.exists(full_path):
        print(f"❌ 找不到文件: {filepath}")
        sys.exit(1)
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    if old_anchor not in content:
        print(f"❌ 在{file_desc}里没找到匹配的代码，官方源码可能已更新")
        sys.exit(1)
    # 先备份
    shutil.copy2(full_path, full_path + '.bak')
    new_content = content.replace(old_anchor, new_block, 1)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"✅ {file_desc} 补丁打成功")

# 1. 修改 SleepTimer.kt
sleep_timer_path = "app/src/main/java/remix/myplayer/util/sleeptimer/SleepTimer.kt"
sleep_timer_old = '''    fun start(minutes: Int) {
        stop()
        mTimer = Object()
        mStartMinute = minutes
        mStartMillisecond = minutes * 60 * 1000L
        mAlarmManager.setExactAndAllowWhileIdle(
            AlarmManager.ELAPSED_REALTIME_WAKEUP,
            SystemClock.elapsedRealtime() + mStartMillisecond,
            mPendingIntent
        )
        mListenerSet.forEach {
            it.onStart(mStartMinute)
        }
        Toast.makeText(mContext, mContext.getString(R.string.sleep_timer_will_stop_in_minutes, minutes), Toast.LENGTH_SHORT).show()
    }'''
sleep_timer_new = '''    fun start(minutes: Int, remember: Boolean = true) {
        stop()
        mTimer = Object()
        mStartMinute = minutes
        mStartMillisecond = minutes * 60 * 1000L
        mAlarmManager.setExactAndAllowWhileIdle(
            AlarmManager.ELAPSED_REALTIME_WAKEUP,
            SystemClock.elapsedRealtime() + mStartMillisecond,
            mPendingIntent
        )
        mListenerSet.forEach {
            it.onStart(mStartMinute)
        }
        // 记忆功能：自动保存开启状态和时长
        if (remember) {
            SPUtil.putValue(mContext, SPUtil.TIMER_DEFAULT, true)
            SPUtil.putValue(mContext, SPUtil.TIMER_DURATION, minutes)
        }
        Toast.makeText(mContext, mContext.getString(R.string.sleep_timer_will_stop_in_minutes, minutes), Toast.LENGTH_SHORT).show()
    }'''
replace_or_fail(sleep_timer_path, sleep_timer_old, sleep_timer_new, "SleepTimer.kt 启动定时")

# 修改取消方法：取消时清除记忆
sleep_timer_cancel_old = '''    fun cancel() {
        mAlarmManager.cancel(mPendingIntent)
        mTimer = null
        mStartMinute = 0
        mStartMillisecond = 0
        mListenerSet.forEach {
            it.onCancel()
        }
    }'''
sleep_timer_cancel_new = '''    fun cancel(clearMemory: Boolean = true) {
        mAlarmManager.cancel(mPendingIntent)
        mTimer = null
        mStartMinute = 0
        mStartMillisecond = 0
        mListenerSet.forEach {
            it.onCancel()
        }
        // 记忆功能：手动取消时清除记忆，下次启动不自动开启
        if (clearMemory) {
            SPUtil.putValue(mContext, SPUtil.TIMER_DEFAULT, false)
        }
    }'''
replace_or_fail(sleep_timer_path, sleep_timer_cancel_old, sleep_timer_cancel_new, "SleepTimer.kt 取消定时")

# 2. 修改 MusicService.kt，onCreate时自动恢复定时
music_service_path = "app/src/main/java/remix/myplayer/service/MusicService.kt"
service_oncreate_old = '''        mMediaSession = MediaSessionCompat(this, "com.remix.myplayer.service.MusicService")
        mMediaSession?.setCallback(mMediaSessionCallback)
        initAsync()
        isRunning = true
        val service = Intent(this, MusicService::class.java)
        startForeground(NOTIFICATION_ID, NotificationUtil.createNotify(this, service))
    }'''
service_oncreate_new = '''        mMediaSession = MediaSessionCompat(this, "com.remix.myplayer.service.MusicService")
        mMediaSession?.setCallback(mMediaSessionCallback)
        initAsync()
        isRunning = true
        val service = Intent(this, MusicService::class.java)
        startForeground(NOTIFICATION_ID, NotificationUtil.createNotify(this, service))
        // 定时记忆：服务启动后延迟2秒自动恢复上次的定时
        Handler(Looper.getMainLooper()).postDelayed({
            val isDefault = SPUtil.getValue(this, SPUtil.TIMER_DEFAULT, false) as Boolean
            if (isDefault) {
                val duration = SPUtil.getValue(this, SPUtil.TIMER_DURATION, 30) as Int
                if (duration > 0) {
                    SleepTimer.instance.start(duration, remember = false)
                }
            }
        }, 2000)
    }'''
replace_or_fail(music_service_path, service_oncreate_old, service_oncreate_new, "MusicService.kt 启动恢复定时")

print("🎉 所有补丁已全部打成功！")
