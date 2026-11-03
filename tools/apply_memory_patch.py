#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APlayer 定时关闭「记忆功能」自动打补丁脚本

做了什么：
  1) 在 SleepTimer.kt 中：开始定时关闭时，自动把本次时长（秒）和「默认开启」标记写入配置；
     用户主动取消定时时，清除「默认开启」标记。
  2) 在 MusicService.kt 中：播放服务启动时，如果上次开启了定时关闭，
     就自动按上次的时长重新开始倒计时（到点照常停止播放 / 退出）。

用法（在仓库根目录执行）：
    python3 tools/apply_memory_patch.py
也可以手动指定仓库根目录：
    python3 tools/apply_memory_patch.py /path/to/APlayer
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if len(sys.argv) > 1:
    REPO_ROOT = os.path.abspath(sys.argv[1])

SLEEP_TIMER = os.path.join(
    REPO_ROOT, "app/src/main/java/remix/myplayer/helper/SleepTimer.kt")
MUSIC_SERVICE = os.path.join(
    REPO_ROOT, "app/src/main/java/remix/myplayer/service/MusicService.kt")

SLEEP_TIMER_PATCHES = [
    (
        "import remix.myplayer.util.ToastUtil",
        "import remix.myplayer.util.ToastUtil\n"
        "import remix.myplayer.util.SPUtil\n"
        "import remix.myplayer.util.SPUtil.SETTING_KEY",
    ),
    (
        "        instance = SleepTimer(duration, 1000)\n"
        "        instance?.start()",
        "        instance = SleepTimer(duration, 1000)\n"
        "        instance?.start()\n"
        "        // 记忆功能：保存本次时长(秒)并标记为默认开启\n"
        "        SPUtil.putValue(context, SETTING_KEY.NAME, SETTING_KEY.TIMER_DEFAULT, true)\n"
        "        SPUtil.putValue(\n"
        "            context, SETTING_KEY.NAME, SETTING_KEY.TIMER_DURATION, (duration / 1000).toInt()\n"
        "        )",
    ),
    (
        "          } else {\n"
        "            instance?.cancel()\n"
        "          }\n"
        "          instance = null",
        "          } else {\n"
        "            instance?.cancel()\n"
        "            // 记忆功能：用户主动取消后，下次启动不再自动开启\n"
        "            SPUtil.putValue(context, SETTING_KEY.NAME, SETTING_KEY.TIMER_DEFAULT, false)\n"
        "          }\n"
        "          instance = null",
    ),
]

MUSIC_SERVICE_PATCHES = [
    (
        "    //定时关闭\n"
        "    SleepTimer.addCallback(object : SleepTimer.Callback {",
        "    //记忆功能：若上次开启了定时关闭，本次启动自动恢复\n"
        "    if (!SleepTimer.isTicking()) {\n"
        "      val autoTimerDefault =\n"
        "          SPUtil.getValue(this, SETTING_KEY.NAME, SETTING_KEY.TIMER_DEFAULT, false)\n"
        "      val autoTimerDuration =\n"
        "          SPUtil.getValue(this, SETTING_KEY.NAME, SETTING_KEY.TIMER_DURATION, -1)\n"
        "      if (autoTimerDefault && autoTimerDuration > 0) {\n"
        "        SleepTimer.toggleTimer(autoTimerDuration.toLong() * 1000)\n"
        "      }\n"
        "    }\n"
        "\n"
        "    //定时关闭\n"
        "    SleepTimer.addCallback(object : SleepTimer.Callback {",
    ),
]


def apply(path, replacements, name):
    if not os.path.isfile(path):
        print("[失败] 找不到文件: %s" % path)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    for idx, (old, new) in enumerate(replacements, 1):
        if new in text:
            print("  - %s 第%d处: 已包含改动，跳过" % (name, idx))
            continue
        cnt = text.count(old)
        if cnt != 1:
            print("[失败] %s 第%d处锚点匹配到 %d 次（应为 1 次）" % (name, idx, cnt))
            print("       锚点片段: %r" % old[:90])
            sys.exit(1)
        text = text.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("[完成] %s" % name)


def main():
    print("正在为 APlayer 打入「定时关闭记忆功能」...")
    apply(SLEEP_TIMER, SLEEP_TIMER_PATCHES, "SleepTimer.kt")
    apply(MUSIC_SERVICE, MUSIC_SERVICE_PATCHES, "MusicService.kt")
    print("补丁应用完成。接下来可执行 ./gradlew app:assembleCiRelease 构建 APK。")


if __name__ == "__main__":
    main()
