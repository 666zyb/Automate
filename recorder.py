import threading
import time

class Recorder:
    def __init__(self, record_move=False):
        self.is_recording = False
        self.events = []
        self._record_thread = None
        self._start_time = None
        self.scaling_factor = 1.0
        self.record_move = record_move

    @staticmethod
    def get_scaling_factor():
        import ctypes
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        user32.SetProcessDPIAware()
        hdc = user32.GetDC(0)
        logical_width = user32.GetSystemMetrics(0)
        physical_width = gdi32.GetDeviceCaps(hdc, 118)
        return physical_width / logical_width

    @staticmethod
    def get_screen_size():
        import ctypes
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

    def start_record(self):
        self.is_recording = True
        self.events = []
        self._start_time = time.time()
        from pynput.mouse import Controller as MouseController
        mouse_ctl = MouseController()
        self.scaling_factor = self.get_scaling_factor()
        w, h = self.get_screen_size()
        print(f"录制时缩放比例: {self.scaling_factor:.2f}, 屏幕分辨率: {w}x{h}")
        self.events.append(("start", mouse_ctl.position, 0))
        self._record_thread = threading.Thread(target=self._record_loop)
        self._record_thread.start()

    def stop_record(self):
        self.is_recording = False
        if self._record_thread:
            self._record_thread.join()
            self._record_thread = None

    def _record_loop(self):
        def on_move(x, y):
            if self.is_recording and self.record_move:
                self.events.append(("move", (x, y), time.time() - self._start_time))
        def on_click(x, y, button, pressed):
            if self.is_recording:
                self.events.append(("click", (x, y, button.name, pressed), time.time() - self._start_time))
        def on_scroll(x, y, dx, dy):
            if self.is_recording:
                self.events.append(("scroll", (x, y, dx, dy), time.time() - self._start_time))
        def on_press(key):
            if self.is_recording:
                k = str(key)
                self.events.append(("key_press", k, time.time() - self._start_time))
        def on_release(key):
            if self.is_recording:
                k = str(key)
                self.events.append(("key_release", k, time.time() - self._start_time))
        from pynput import mouse, keyboard
        mouse_args = dict(on_click=on_click, on_scroll=on_scroll)
        if self.record_move:
            mouse_args['on_move'] = on_move
        with mouse.Listener(**mouse_args) as m_listener, \
             keyboard.Listener(on_press=on_press, on_release=on_release) as k_listener:
            while self.is_recording:
                time.sleep(0.01)

    def save_record(self, filepath):
        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({"scaling_factor": self.scaling_factor, "events": self.events}, f, ensure_ascii=False, indent=2)

    def load_record(self, filepath):
        import json
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.events = data["events"] if isinstance(data, dict) and "events" in data else data
            self.scaling_factor = data.get("scaling_factor", 1.0) if isinstance(data, dict) else 1.0

    def playback(self):
        from pynput.mouse import Controller as MouseController, Button
        from pynput.keyboard import Controller as KeyboardController, Key, Listener as KeyboardListener
        import threading
        mouse_ctl = MouseController()
        keyboard_ctl = KeyboardController()
        if not self.events:
            return
        playback_scale = self.get_scaling_factor()
        record_scale = self.scaling_factor
        w, h = self.get_screen_size()
        print(f"回放时缩放比例: {playback_scale:.2f}, 屏幕分辨率: {w}x{h}")
        def scale_pos(pos):
            x, y = pos
            return (x * playback_scale / record_scale, y * playback_scale / record_scale)
        start_pos = next((data for etype, data, t in self.events if etype == "start"), None)
        if start_pos:
            mouse_ctl.position = scale_pos(start_pos)
            time.sleep(0.2)
        start_time = time.time()
        prev_move_time = None
        prev_move_pos = None
        self._stop_playback = False  # 新增：中断标志
        # 新增：热键监听线程
        def on_press(key):
            try:
                if key == Key.space and self._win_pressed:
                    self._stop_playback = True
                    return False  # 停止监听
                if key == Key.cmd or key == Key.cmd_l or key == Key.cmd_r:
                    self._win_pressed = True
            except Exception:
                pass
        def on_release(key):
            try:
                if key == Key.cmd or key == Key.cmd_l or key == Key.cmd_r:
                    self._win_pressed = False
            except Exception:
                pass
        self._win_pressed = False
        listener = KeyboardListener(on_press=on_press, on_release=on_release)
        listener.start()
        # 新增：str转Key或字符
        def str_to_key(s):
            from pynput.keyboard import Key
            if s.startswith('Key.'):
                try:
                    return getattr(Key, s[4:])
                except Exception:
                    return s
            if len(s) == 3 and s.startswith("'") and s.endswith("'"):
                return s[1]
            return s
        try:
            for etype, data, t in self.events:
                if self._stop_playback:
                    print("检测到Win+空格，中断任务执行！")
                    break
                now = time.time() - start_time
                wait = t - now
                if wait > 0:
                    time.sleep(wait)
                if self._stop_playback:
                    print("检测到Win+空格，中断任务执行！")
                    break
                if etype == "move":
                    x, y = scale_pos(data)
                    if prev_move_time is not None and prev_move_pos is not None:
                        interval = t - prev_move_time
                        steps = max(int(interval / 0.01), 1)
                        x0, y0 = prev_move_pos
                        for step in range(1, steps + 1):
                            if self._stop_playback:
                                print("检测到Win+空格，中断任务执行！")
                                break
                            nx = x0 + (x - x0) * step / steps
                            ny = y0 + (y - y0) * step / steps
                            mouse_ctl.position = (nx, ny)
                            time.sleep(interval / steps)
                        if self._stop_playback:
                            break
                    else:
                        mouse_ctl.position = (x, y)
                    prev_move_time = t
                    prev_move_pos = (x, y)
                elif etype == "click":
                    x, y, button, pressed = data
                    btn = getattr(Button, button)
                    mouse_ctl.position = scale_pos((x, y))
                    if pressed:
                        time.sleep(0.5)
                        mouse_ctl.press(btn)
                    else:
                        mouse_ctl.release(btn)
                elif etype == "scroll":
                    x, y, dx, dy = data
                    mouse_ctl.position = scale_pos((x, y))
                    mouse_ctl.scroll(dx, dy)
                elif etype == "key_press":
                    try:
                        keyboard_ctl.press(str_to_key(data))
                    except Exception:
                        pass
                elif etype == "key_release":
                    try:
                        keyboard_ctl.release(str_to_key(data))
                    except Exception:
                        pass
        finally:
            listener.stop()

if __name__ == "__main__":
    mode = input("输入1录制，2回放：")
    if mode == "1":
        move_choice = input("是否录制鼠标移动轨迹？(y/n): ").strip().lower()
        record_move = move_choice == 'y'
        rec = Recorder(record_move=record_move)
        print("按回车开始录制，录制时可操作鼠标和键盘，再按回车停止录制...")
        input()
        rec.start_record()
        input("录制中...按回车停止\n")
        rec.stop_record()
        print(f"录制完成，共{len(rec.events)}条事件。保存到record.json。")
        rec.save_record("record.json")
    elif mode == "2":
        rec = Recorder()
        rec.load_record("record.json")
        input("按回车开始回放（请勿操作鼠标键盘）...")
        rec.playback()
        print("回放结束。")