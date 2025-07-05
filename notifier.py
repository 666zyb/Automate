import platform
import os
import time


def play_sound(sound_file, sound_dir='sounds'):
    """
    播放自定义声音文件（如ding.wav），找不到时回退到系统音。支持Windows、macOS、Linux。
    默认从sounds/目录查找声音文件。
    """
    # 如果sound_file不是绝对路径，则拼接sound_dir
    if not os.path.isabs(sound_file):
        sound_file = os.path.join(sound_dir, sound_file)
    sys = platform.system()
    # 优先播放自定义声音
    if os.path.exists(sound_file):
        if sys == 'Windows':
            import winsound
            try:
                winsound.PlaySound(sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
                time.sleep(1.5)
            except Exception as e:
                print("播放自定义声音失败，使用系统音。", e)
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
        elif sys == 'Darwin':  # macOS
            os.system(f'afplay "{sound_file}"')
        elif sys == 'Linux':
            # 优先paplay, 其次aplay, 最后ffplay
            if os.system('which paplay > /dev/null 2>&1') == 0:
                os.system(f'paplay "{sound_file}"')
            elif os.system('which aplay > /dev/null 2>&1') == 0:
                os.system(f'aplay "{sound_file}"')
            elif os.system('which ffplay > /dev/null 2>&1') == 0:
                os.system(f'ffplay -nodisp -autoexit "{sound_file}"')
            else:
                print("未找到合适的播放器，无法播放自定义声音。")
        else:
            print("未知系统，无法播放自定义声音。")
    else:
        # 文件不存在时回退到系统音
        if sys == 'Windows':
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        elif sys == 'Darwin':
            os.system('afplay /System/Library/Sounds/Ping.aiff')
        elif sys == 'Linux':
            if os.system('which paplay > /dev/null 2>&1') == 0:
                os.system('paplay /usr/share/sounds/freedesktop/stereo/bell.oga')
            elif os.system('which aplay > /dev/null 2>&1') == 0:
                os.system('aplay /usr/share/sounds/alsa/Front_Center.wav')
            else:
                os.system('beep')