from PyQt5.QtCore import QThread, pyqtSignal
import pyautogui, pytesseract, cv2, numpy as np, time, re, os, sys
from datetime import datetime
from PIL import Image
from task_manager import TaskManager
from notifier import play_sound

class MonitorWorker(QThread):
    status_signal = pyqtSignal(str)

    def __init__(self, template_path='template.png', log_file='monitor_log.txt', parent=None):
        super().__init__(parent)
        self.template_path = template_path
        self.log_file = log_file
        self.running = False

    def run(self):
        # 兼容PyInstaller打包和开发环境的tesseract路径
        def resource_path(relative_path):
            if hasattr(sys, '_MEIPASS'):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            return os.path.join(base_path, relative_path)
        tesseract_path = resource_path(os.path.join('Tesseract-OCR', 'tesseract.exe'))
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        if not os.path.exists(self.template_path):
            self.status_signal.emit('未找到template.png')
            return
        # 读取数据库阈值
        db = TaskManager()
        c = db.conn.cursor()
        c.execute('SELECT min_threshold, max_threshold FROM monitor_thresholds WHERE template_path=? ORDER BY id DESC LIMIT 1', (self.template_path,))
        row = c.fetchone()
        min_threshold, max_threshold = None, None
        if row:
            min_threshold, max_threshold = row
        # 用PIL读取模板图片，兼容中文路径和多格式
        try:
            pil_template = Image.open(self.template_path)
            template = cv2.cvtColor(np.array(pil_template), cv2.COLOR_RGB2GRAY)
        except Exception as e:
            self.status_signal.emit(f'模板图片读取失败: {e}')
            return
        w, h = template.shape[::-1]
        last_value = None
        self.running = True
        self.status_signal.emit('监控中')
        while self.running:
            screenshot = pyautogui.screenshot()
            screenshot.save('screen.png')
            img_rgb = cv2.imread('screen.png')
            img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
            res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            threshold = 0.7
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if max_val < threshold:
                msg = f'[{now}] 目标区域未找到！'
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(msg + '\n')
                time.sleep(1)
                if os.path.exists('screen.png'):
                    os.remove('screen.png')
                continue
            top_left = max_loc
            region = (top_left[0], top_left[1], w, h)
            target_img = pyautogui.screenshot(region=region)
            text = pytesseract.image_to_string(target_img, config='--psm 7')
            match = re.search(r'\d+\.?\d*', text)
            value = match.group(0) if match else text.strip()
            if value != last_value:
                msg = f'{now} 识别数值: {value}'
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(msg + '\n')
                last_value = value
            # 阈值判断
            try:
                num_value = float(value)
                alert = False
                if min_threshold is not None and num_value < min_threshold:
                    alert = True
                if max_threshold is not None and num_value > max_threshold:
                    alert = True
                if alert:
                    play_sound('y1478.wav')
                    self.status_signal.emit(f'数值超出阈值: {num_value}')
            except Exception:
                pass
            time.sleep(0.5)
            if os.path.exists('screen.png'):
                os.remove('screen.png')
        self.status_signal.emit('已停止')

    def stop(self):
        self.running = False