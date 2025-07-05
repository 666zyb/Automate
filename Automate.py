import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QSizePolicy, QLineEdit, QDateTimeEdit, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QFrame, QDialog, QTimeEdit, QSpinBox, QFileDialog, QTextEdit, QComboBox
)
from PyQt5.QtGui import QFont, QIcon, QPainter, QColor
from PyQt5.QtCore import Qt, QSize, QTime, QTimer, QObject
from task_manager import TaskManager
from recorder import Recorder
from functools import partial
from monitor_worker import MonitorWorker

class TaskScheduler(QObject):
    def __init__(self, task_name, run_time: QTime, repeat_count: int, filename, parent=None):
        super().__init__(parent)
        self.task_name = task_name
        self.run_time = run_time
        self.repeat_count = repeat_count
        self.filename = filename
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_and_run)
        self.timer.start(1000)  # 每1秒检查一次
        self.has_run_today = False
        self.status = "等待中"
        self.paused = False
        self.deadline_str = None  # 截止时间字符串
        self.repeat_interval = 1  # 重复间隔

    def pause(self):
        if not self.paused:
            self.paused = True
            self.timer.stop()

    def resume(self):
        if self.paused:
            self.paused = False
            self.timer.start(1000)

    def check_and_run(self):
        if self.paused:
            return
        # 检查截止时间
        from PyQt5.QtCore import QDateTime
        if self.deadline_str:
            deadline_dt = QDateTime.fromString(self.deadline_str, "yyyy-MM-dd HH:mm")
            if deadline_dt.isValid() and deadline_dt < QDateTime.currentDateTime():
                self.pause()
                # 只刷新表格，不弹窗
                if hasattr(self.parent(), 'refresh_status_table'):
                    self.parent().refresh_status_table()
                return
        now = QTime.currentTime()
        # 直接到点执行，不弹窗
        if now.hour() == self.run_time.hour() and now.minute() == self.run_time.minute():
            if not self.has_run_today:
                self.status = "执行中"
                self.run_task()
                self.has_run_today = True
                self.status = "等待中"
        elif now > self.run_time and self.has_run_today:
            if now.hour() == 0 and now.minute() == 0:
                self.has_run_today = False



    def run_task(self):
        from recorder import Recorder
        import time
        # 隐藏程序窗口
        if hasattr(self.parent(), 'hide'):
            self.parent().hide()
        rec = Recorder()
        rec.load_record(self.filename)
        for i in range(self.repeat_count):
            rec.playback()
            if i < self.repeat_count - 1:
                time.sleep(self.repeat_interval)
        # 任务执行完成后显示窗口
        if hasattr(self.parent(), 'show'):
            self.parent().show()

    def next_run_time(self):
        now = QTime.currentTime()
        if now < self.run_time:
            return self.run_time.toString("HH:mm")
        else:
            return self.run_time.toString("HH:mm")

class RecordIndicator(QWidget):
    def __init__(self, stop_callback, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(80, 80)
        self.stop_callback = stop_callback

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # 外圈
        painter.setBrush(QColor(220, 0, 0, 180))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(10, 10, 60, 60)
        # 内圈
        painter.setBrush(QColor(255, 0, 0, 255))
        painter.drawEllipse(25, 25, 30, 30)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.stop_callback()
            self.close()

class RunConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("运行设置")
        self.setFixedSize(320, 340)
        self.setStyleSheet('''
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e6f7fa, stop:1 #b2f1f1);
                border-radius: 18px;
            }
            QLabel {
                font-size: 1.13em;
                color: #19a3a3;
            }
            QTimeEdit, QSpinBox, QLineEdit {
                background: #f5fafd;
                border: 1.5px solid #e0f0f0;
                border-radius: 10px;
                padding-left: 12px;
                padding-right: 12px;
                font-size: 1.13em;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #19e3e3, stop:1 #0bbaba);
                color: white;
                border-radius: 12px;
                font-weight: bold;
                min-width: 80px;
                min-height: 32px;
                margin-top: 8px;
            }
            QPushButton:hover {
                background: #19a3a3;
                color: #fff;
            }
        ''')
        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(24, 24, 24, 24)

        label_time = QLabel("每天几点执行：")
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime.currentTime())

        label_repeat = QLabel("每次执行重复次数：")
        self.repeat_spin = QSpinBox()
        self.repeat_spin.setRange(1, 100)
        self.repeat_spin.setValue(1)

        label_interval = QLabel("重复间隔（秒）：")
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 3600)
        self.interval_spin.setValue(1)

        layout.addWidget(label_time)
        layout.addWidget(self.time_edit)
        layout.addWidget(label_repeat)
        layout.addWidget(self.repeat_spin)
        layout.addWidget(label_interval)
        layout.addWidget(self.interval_spin)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("确定")
        btn_cancel = QPushButton("取消")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch(1)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)

    def get_config(self):
        return self.time_edit.time(), self.repeat_spin.value(), self.interval_spin.value()

class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Automate")
        self.setWindowIcon(QIcon("icon.ico"))  # 设置窗口图标
        self.setMinimumSize(800, 600)
        self.central = QWidget()
        self.setCentralWidget(self.central)
        # 顶部LOGO栏
        self.logo_bar = QWidget()
        self.logo_bar.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #19e3e3, stop:1 #0bbaba);")
        self.logo_layout = QHBoxLayout(self.logo_bar)
        self.logo_layout.setContentsMargins(20, 8, 0, 8)
        self.logo_layout.setSpacing(0)
        self.logo = QLabel()
        self.logo.setText("<span style='font-size:20px;font-weight:bold;color:white;'>🤖 NLAutomate</span>")
        self.logo.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.logo_layout.addWidget(self.logo)
        self.logo_layout.addStretch(1)
        # 主体区域（左菜单+右内容）
        self.body_widget = QWidget()
        self.body_layout = QHBoxLayout(self.body_widget)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)
        # 左侧菜单栏
        self.menu_widget = QWidget()
        self.menu_widget.setObjectName("menuWidget")
        self.menu_widget.setMinimumWidth(100)
        self.menu_widget.setMaximumWidth(220)
        self.menu_layout = QVBoxLayout(self.menu_widget)
        self.menu_layout.setContentsMargins(10, 30, 5, 0)
        self.menu_layout.setSpacing(30)
        self.menu_widget.setStyleSheet(
            """
            #menuWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #19e3e3, stop:1 #0bbaba);
                /* border-top-left-radius: 24px; */
                /* border-bottom-left-radius: 24px; */
                box-shadow: 4px 0 24px 0 rgba(0,0,0,0.10);
            }
            """
        )
        # 菜单按钮
        self.menu_buttons = []
        menu_info = [
            ("\U0001F4C4", "创建任务"),
            ("\U0001F4DD", "任务录迹"),
            ("\U0001F4DC", "历史任务"),
            ("\U0001F7E2", "运行状态"),
            ("\U0001F50D", "界面监控")
        ]
        for i, (icon, text) in enumerate(menu_info):
            btn = QPushButton()
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFont(QFont("Microsoft YaHei UI", 10))
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setFixedHeight(32)
            btn.setObjectName(f"menuBtn{i}")
            # 图标和文字分离
            btn.setStyleSheet(self.menu_btn_style(selected=(i==0)))
            btn.setLayoutDirection(Qt.LeftToRight)
            btn.setText("")
            btn_layout = QHBoxLayout(btn)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.setSpacing(6)
            icon_label = QLabel(icon)
            icon_label.setFont(QFont("Microsoft YaHei UI", 14))
            icon_label.setStyleSheet("color: inherit;")
            text_label = QLabel(text)
            text_label.setFont(QFont("Microsoft YaHei UI", 10))
            text_label.setStyleSheet("color: inherit;")
            btn_layout.addWidget(icon_label)
            btn_layout.addWidget(text_label)
            btn_layout.addStretch(1)
            btn.clicked.connect(lambda checked, idx=i: self.select_menu(idx))
            self.menu_layout.addWidget(btn)
            self.menu_buttons.append(btn)
        self.menu_layout.addStretch(1)
        # 右侧内容区
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background:#19e3e3;")
        # 创建任务内容区
        self.create_task_outer = QWidget()
        self.create_task_outer_layout = QHBoxLayout(self.create_task_outer)
        self.create_task_outer_layout.setContentsMargins(0, 0, 0, 0)
        self.create_task_outer_layout.setSpacing(0)
        self.create_task_outer_layout.addStretch(1)
        self.create_task_widget = QWidget()
        self.create_task_widget.setObjectName("createTaskCard")
        self.create_task_layout = QVBoxLayout(self.create_task_widget)
        self.create_task_layout.setContentsMargins(40, 40, 40, 40)
        self.create_task_layout.setSpacing(30)
        # 标题
        self.task_title = QLabel("创建新任务")
        self.task_title.setAlignment(Qt.AlignCenter)
        self.create_task_layout.addWidget(self.task_title)
        # 任务名称
        self.task_name_label = QLabel("任务名称")
        self.create_task_layout.addWidget(self.task_name_label)
        self.task_name_input = QLineEdit()
        self.create_task_layout.addWidget(self.task_name_input)
        # 任务描述
        self.task_desc_label = QLabel("任务描述")
        self.create_task_layout.addWidget(self.task_desc_label)
        self.task_desc_input = QLineEdit()
        self.create_task_layout.addWidget(self.task_desc_input)
        # 任务截止时间
        self.task_deadline_label = QLabel("任务截止时间")
        self.create_task_layout.addWidget(self.task_deadline_label)
        self.task_deadline_input = QDateTimeEdit()
        self.task_deadline_input.setCalendarPopup(True)
        self.create_task_layout.addWidget(self.task_deadline_input)
        # 创建按钮
        self.create_btn = QPushButton("创建")
        self.create_task_layout.addWidget(self.create_btn)
        self.create_task_outer_layout.addWidget(self.create_task_widget, 60)
        self.create_task_outer_layout.addStretch(1)
        # 历史任务内容区
        self.history_task_widget = QWidget()
        self.history_task_widget.setObjectName("historyTaskCard")
        self.history_task_layout = QVBoxLayout(self.history_task_widget)
        self.history_task_layout.setContentsMargins(40, 40, 40, 40)
        self.history_task_layout.setSpacing(30)
        # 标题
        self.history_title = QLabel("历史任务")
        self.history_title.setAlignment(Qt.AlignCenter)
        self.history_task_layout.addWidget(self.history_title)
        # 分割线
        self.history_line = QFrame()
        self.history_line.setFrameShape(QFrame.HLine)
        self.history_task_layout.addWidget(self.history_line)
        # 表格
        self.history_table = QTableWidget(0, 4)
        self.history_table.setHorizontalHeaderLabels(["任务名称", "截止时间", "状态", "操作"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.history_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.history_table.verticalHeader().setVisible(False)
        # 设置列宽比例：任务名称20%，截止时间40%，状态10%，操作30%
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.history_table.setColumnWidth(2, 60)
        self.history_table.setColumnWidth(1, 200)
        self.history_task_layout.addWidget(self.history_table)
        self.history_task_widget.setStyleSheet('''
            #historyTaskCard {
                background: rgba(255,255,255,0.92);
                border-radius: 24px;
                box-shadow: 0 4px 32px 0 rgba(25,163,163,0.10);
            }
            QTableWidget {
                background: #fafdff;
                border: 1.5px solid #e0f0f0;
                border-radius: 12px;
                font-size: 1.08em;
                gridline-color: #e0f0f0;
                selection-background-color: #e0f7fa;
                selection-color: #19a3a3;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e6f7fa, stop:1 #b2f1f1);
                color: #19a3a3;
                font-weight: bold;
                font-size: 1.13em;
                border: none;
                height: 38px;
                padding: 6px 0;
            }
            QTableWidget::item {
                border-bottom: 1px solid #e0f0f0;
                padding: 8px 0;
            }
            QTableWidget::item:selected {
                background: #d0f7fa;
                color: #19a3a3;
            }
            QTableWidget::item:alternate {
                background: #f3fbfd;
            }
        ''')
        self.history_table.setAlternatingRowColors(True)
        # 在内容区布局中，添加一个水平布局专门包裹历史任务卡片
        self.history_task_row = QHBoxLayout()
        self.history_task_row.addStretch(1)
        self.history_task_row.addWidget(self.history_task_widget)
        self.history_task_row.addStretch(1)
        # 运行状态内容区
        self.status_widget = QWidget()
        self.status_widget.setObjectName("statusCard")
        self.status_layout = QVBoxLayout(self.status_widget)
        self.status_layout.setContentsMargins(40, 40, 40, 40)
        self.status_layout.setSpacing(30)
        # 标题
        self.status_title = QLabel("运行状态")
        self.status_title.setAlignment(Qt.AlignCenter)
        self.status_layout.addWidget(self.status_title)
        # 分割线
        self.status_line = QFrame()
        self.status_line.setFrameShape(QFrame.HLine)
        self.status_layout.addWidget(self.status_line)
        # 定时任务表格
        self.status_table = QTableWidget(0, 6)
        self.status_table.setHorizontalHeaderLabels(["任务名称", "执行时间", "重复次数", "下次执行时间", "状态", "操作"])
        self.status_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.status_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.status_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.status_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.status_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.status_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.status_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.status_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.status_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.status_table.verticalHeader().setVisible(False)
        self.status_layout.addWidget(self.status_table)
        self.status_widget.setStyleSheet('''
            #statusCard {
                background: rgba(255,255,255,0.92);
                border-radius: 24px;
                box-shadow: 0 4px 32px 0 rgba(25,163,163,0.10);
            }
            QTableWidget {
                background: #fafdff;
                border: 1.5px solid #e0f0f0;
                border-radius: 10px;
                font-size: 1em;
            }
            QHeaderView::section {
                background: #e6f7fa;
                color: #19a3a3;
                font-weight: bold;
                border: none;
                height: 32px;
            }
            QTableWidget::item {
                border-bottom: 1px solid #e0f0f0;
            }
        ''')
        self.status_widget.hide()  # 默认隐藏
        # 用水平布局包裹，保证居中
        self.status_row = QHBoxLayout()
        self.status_row.addStretch(1)
        self.status_row.addWidget(self.status_widget)
        self.status_row.addStretch(1)
        # 任务录迹内容区
        self.record_widget = QWidget()
        self.record_widget.setObjectName("recordCard")
        self.record_layout = QVBoxLayout(self.record_widget)
        self.record_layout.setContentsMargins(40, 40, 40, 40)
        self.record_layout.setSpacing(30)
        # 标题
        self.record_title = QLabel("任务录迹")
        self.record_title.setAlignment(Qt.AlignCenter)
        self.record_layout.addWidget(self.record_title)
        # 分割线
        record_line = QFrame()
        record_line.setFrameShape(QFrame.HLine)
        self.record_layout.addWidget(record_line)
        # 说明文字
        self.record_desc = QLabel("可录制鼠标和键盘的操作，实现自动化回放。<br>点击下方按钮开始或停止录制。")
        self.record_desc.setAlignment(Qt.AlignCenter)
        self.record_desc.setWordWrap(True)
        self.record_desc.setTextFormat(Qt.RichText)
        self.record_layout.addWidget(self.record_desc)
        # 录迹任务表格
        self.record_table = QTableWidget(0, 4)
        self.record_table.setHorizontalHeaderLabels(["任务名称", "是否录迹", "截止时间", "操作"])
        self.record_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)          # 任务名称
        self.record_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)            # 是否录迹
        self.record_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)          # 截止时间
        self.record_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)            # 操作
        self.record_table.setColumnWidth(1, 100)
        self.record_table.setColumnWidth(3, 120)
        self.record_table.setColumnWidth(2, 160)
        self.record_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.record_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.record_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.record_table.verticalHeader().setVisible(False)
        self.record_layout.addWidget(self.record_table)
        # 按钮区
        record_btn_row = QHBoxLayout()
        self.start_record_btn = QPushButton("开始录制")
        self.stop_record_btn = QPushButton("停止录制")
        self.stop_record_btn.setEnabled(False)
        record_btn_row.addStretch(1)
        record_btn_row.addWidget(self.start_record_btn)
        record_btn_row.addSpacing(20)
        record_btn_row.addWidget(self.stop_record_btn)
        record_btn_row.addStretch(1)
        self.record_layout.addLayout(record_btn_row)
        self.record_widget.setStyleSheet('''
            #recordCard {
                background: rgba(255,255,255,0.92);
                border-radius: 24px;
                box-shadow: 0 4px 32px 0 rgba(25,163,163,0.10);
            }
            QLabel {
                font-size: 1.13em;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #19e3e3, stop:1 #0bbaba);
                color: white;
                border-radius: 12px;
                font-weight: bold;
                min-width: 120px;
                min-height: 38px;
                padding: 8px 32px;
                margin-top: 8px;
            }
            QPushButton:disabled {
                background: #bdbdbd;
                color: #fff;
            }
            QPushButton:hover:!disabled {
                background: #19a3a3;
                color: #fff;
            }
        ''')
        self.record_widget.hide()
        # 用水平布局包裹，保证居中
        self.record_row = QHBoxLayout()
        self.record_row.addStretch(1)
        self.record_row.addWidget(self.record_widget)
        self.record_row.addStretch(1)
        # 界面监控内容区
        self.monitor_widget = QWidget()
        self.monitor_widget.setObjectName("monitorCard")
        self.monitor_layout = QVBoxLayout(self.monitor_widget)
        self.monitor_layout.setContentsMargins(40, 40, 40, 40)
        self.monitor_layout.setSpacing(30)
        # 标题
        self.record_title = QLabel("界面监控")
        self.record_title.setAlignment(Qt.AlignCenter)
        self.monitor_layout.addWidget(self.record_title)
        # 分割线
        record_line = QFrame()
        record_line.setFrameShape(QFrame.HLine)
        self.monitor_layout.addWidget(record_line)
        self.monitor_status = QLabel("状态：未启动")
        self.monitor_status.setStyleSheet("font-size:16px;color:#19a3a3;")
        self.monitor_layout.addWidget(self.monitor_status)
        self.monitor_template_path = QLabel("当前模板：template.png")
        self.monitor_template_path.setStyleSheet("font-size:13px;color:#888;")
        self.monitor_layout.addWidget(self.monitor_template_path)

        # 阈值设置区（区间）
        threshold_row = QHBoxLayout()
        self.threshold_min_input = QLineEdit()
        self.threshold_min_input.setPlaceholderText("最小阈值（可选）")
        self.threshold_max_input = QLineEdit()
        self.threshold_max_input.setPlaceholderText("最大阈值（可选）")
        self.save_threshold_btn = QPushButton("保存阈值")
        threshold_row.addWidget(QLabel("提醒区间："))
        threshold_row.addWidget(self.threshold_min_input)
        threshold_row.addWidget(QLabel("≤ 数值 ≤"))
        threshold_row.addWidget(self.threshold_max_input)
        threshold_row.addWidget(self.save_threshold_btn)
        self.monitor_layout.addLayout(threshold_row)
        self.monitor_threshold = (None, None)  # (min_value, max_value)
        # 监控任务ID（用于更新）
        self.current_monitor_id = None
        def save_threshold():
            min_text = self.threshold_min_input.text().strip()
            max_text = self.threshold_max_input.text().strip()
            min_value = float(min_text) if min_text else None
            max_value = float(max_text) if max_text else None
            if min_value is not None and max_value is not None and min_value > max_value:
                QMessageBox.warning(self, "输入错误", "最小阈值不能大于最大阈值！")
                return
            self.monitor_threshold = (min_value, max_value)
            name = "默认监控任务"  # 可扩展为用户输入
            template_path = getattr(self, 'monitor_selected_template', 'template.png')
            # 新增或更新monitor_thresholds表
            if self.current_monitor_id is None:
                self.current_monitor_id = self.task_manager.add_monitor_threshold(name, template_path, min_value, max_value)
            else:
                self.task_manager.update_monitor_threshold(self.current_monitor_id, min_threshold=min_value, max_threshold=max_value, template_path=template_path)
            msg = ""
            if min_value is not None and max_value is not None:
                msg = f"提醒区间：{min_value} ≤ 数值 ≤ {max_value}"
            elif min_value is not None:
                msg = f"提醒条件：数值 ≥ {min_value}"
            elif max_value is not None:
                msg = f"提醒条件：数值 ≤ {max_value}"
            else:
                msg = "未设置阈值，默认不提醒"
            QMessageBox.information(self, "阈值设置", msg)
        self.save_threshold_btn.clicked.connect(save_threshold)

        btn_row = QHBoxLayout()
        self.monitor_select_btn = QPushButton("选择图片")
        self.monitor_start_btn = QPushButton("开始监控")
        self.monitor_stop_btn = QPushButton("停止监控")
        self.monitor_log_btn = QPushButton("查看日志")
        self.monitor_stop_btn.setEnabled(False)
        btn_row.addWidget(self.monitor_select_btn)
        btn_row.addWidget(self.monitor_start_btn)
        btn_row.addWidget(self.monitor_stop_btn)
        btn_row.addWidget(self.monitor_log_btn)
        self.monitor_layout.addLayout(btn_row)

        self.monitor_worker = None
        self.monitor_selected_template = 'template.png'  # 默认

        def select_template():
            file_path, _ = QFileDialog.getOpenFileName(self, "选择模板图片", "", "图片文件 (*.png *.jpg *.bmp)")
            if file_path:
                self.monitor_template_path.setText(f"当前模板：{file_path}")
                self.monitor_selected_template = file_path

        def start_monitor():
            template_path = getattr(self, 'monitor_selected_template', 'template.png')
            # 启动监控前清空日志
            try:
                with open('monitor_log.txt', 'w', encoding='utf-8') as f:
                    f.write('')
            except Exception as e:
                pass
            if self.monitor_worker is None or not self.monitor_worker.isRunning():
                self.monitor_worker = MonitorWorker(template_path=template_path)
                self.monitor_worker.status_signal.connect(lambda s: self.monitor_status.setText(f"状态：{s}"))
                self.monitor_worker.start()
                self.monitor_start_btn.setEnabled(False)
                self.monitor_stop_btn.setEnabled(True)

        def stop_monitor():
            if self.monitor_worker and self.monitor_worker.isRunning():
                self.monitor_worker.stop()
                self.monitor_worker.wait()
                self.monitor_start_btn.setEnabled(True)
                self.monitor_stop_btn.setEnabled(False)

        def show_monitor_log():
            dlg = LogViewerDialog(parent=self)
            dlg.exec_()

        self.monitor_select_btn.clicked.connect(select_template)
        self.monitor_start_btn.clicked.connect(start_monitor)
        self.monitor_stop_btn.clicked.connect(stop_monitor)
        self.monitor_log_btn.clicked.connect(show_monitor_log)

        self.monitor_widget.setStyleSheet('''
            #monitorCard {
                background: rgba(255,255,255,0.92);
                border-radius: 24px;
                box-shadow: 0 4px 32px 0 rgba(25,163,163,0.10);
            }
            QLabel {
                font-size: 1.13em;
            }
        ''')
        self.monitor_widget.hide()
        # 用水平布局包裹，保证居中
        self.monitor_row = QHBoxLayout()
        self.monitor_row.addStretch(1)
        self.monitor_row.addWidget(self.monitor_widget)
        self.monitor_row.addStretch(1)
        # 内容区布局
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.addStretch(1)
        self.content_layout.addWidget(self.create_task_outer)
        self.content_layout.addLayout(self.history_task_row)
        self.content_layout.addLayout(self.status_row)
        self.content_layout.addLayout(self.record_row)
        self.content_layout.addLayout(self.monitor_row)
        self.content_layout.addStretch(1)
        # 卡片样式
        self.create_task_widget.setStyleSheet('''
            #createTaskCard {
                background: rgba(255,255,255,0.92);
                border-radius: 24px;
                box-shadow: 0 4px 32px 0 rgba(25,163,163,0.10);
            }
            QLineEdit, QDateTimeEdit {
                background: #f5fafd;
                border: 1.5px solid #e0f0f0;
                border-radius: 10px;
                padding-left: 12px;
                padding-right: 12px;
            }
            QLineEdit:focus, QDateTimeEdit:focus {
                border: 1.5px solid #19e3e3;
                background: #f0fcfc;
            }
            QDateTimeEdit::drop-down {
                width: 40px;
                height: 40px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #19e3e3, stop:1 #0bbaba);
                color: white;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #19a3a3;
                color: #fff;
            }
        ''')
        self.body_layout.addWidget(self.menu_widget, 1)
        self.body_layout.addWidget(self.content_widget, 4)
        self.body_layout.setStretch(0, 1)
        self.body_layout.setStretch(1, 4)
        # 总体布局（LOGO栏+主体区域）
        self.main_layout = QVBoxLayout(self.central)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(self.logo_bar)
        self.main_layout.addWidget(self.body_widget, 1)
        self.create_task_outer.show()      # 显示创建任务卡片
        self.history_task_widget.hide()    # 隐藏历史任务卡片
        self.status_widget.hide()          # 隐藏运行状态卡片
        self.record_widget.hide()          # 隐藏任务录迹卡片
        self.monitor_widget.hide()          # 隐藏界面监控卡片
        # 初始化任务管理器
        self.task_manager = TaskManager()
        # 创建按钮绑定事件
        self.create_btn.clicked.connect(self.handle_create_task)
        # 启动时加载历史任务
        self.load_history_tasks_from_db()
        # 启动时加载录迹任务
        self.load_record_tasks_from_db()
        self.start_record_btn.clicked.connect(self.handle_start_record)
        self.stop_record_btn.clicked.connect(self.handle_stop_record)
        self.current_record_task = None  # 当前录制的任务对象
        self.recorder = None
        self.is_recording = False
        self.record_indicator = None
        self.schedulers = []
        # 启动时自动从数据库恢复定时任务
        for row in self.task_manager.get_schedule_tasks():
            schedule_id, task_name, run_time_str, repeat_count, filename, status = row
            run_time = QTime.fromString(run_time_str, "HH:mm")
            scheduler = TaskScheduler(task_name, run_time, int(repeat_count), filename, self)
            scheduler.db_id = schedule_id
            scheduler.status = status  # 新增：同步数据库状态
            self.schedulers.append(scheduler)
        self.refresh_status_table()
        # 启动时将截止时间设为当前时间
        from PyQt5.QtCore import QDateTime
        self.task_deadline_input.setDateTime(QDateTime.currentDateTime())

    def menu_btn_style(self, selected=False):
        if selected:
            return (
                "QPushButton {background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e6f7fa, stop:1 #b2f1f1); color: #19a3a3; border-radius: 12px; text-align: left; box-shadow: 0 2px 8px 0 rgba(25,163,163,0.10); font-weight: bold;}"
                "QPushButton:hover {background: #d0f0f7; box-shadow: 0 4px 16px 0 rgba(25,163,163,0.18);}"
            )
        else:
            return (
                "QPushButton {background: transparent; color: white; border-radius: 12px; text-align: left;}"
                "QPushButton:hover {background: #d0f0f7; color: #19a3a3; box-shadow: 0 2px 8px 0 rgba(25,163,163,0.10);}"
            )
    def select_menu(self, idx):
        for i, btn in enumerate(self.menu_buttons):
            btn.setStyleSheet(self.menu_btn_style(selected=(i==idx)))
            # 同步按钮内文字颜色
            for j in range(btn.layout().count()):
                w = btn.layout().itemAt(j).widget()
                if isinstance(w, QLabel):
                    if i == idx:
                        w.setStyleSheet("color: #19a3a3;")
                    else:
                        w.setStyleSheet("color: white;")
        # 隐藏所有内容区
        self.create_task_outer.hide()
        self.history_task_widget.hide()
        self.status_widget.hide()
        self.record_widget.hide()
        self.monitor_widget.hide()  # 新增
        if idx == 0:
            self.create_task_outer.show()
            # 切换到创建任务时，截止时间设为当前时间
            from PyQt5.QtCore import QDateTime
            self.task_deadline_input.setDateTime(QDateTime.currentDateTime())
        elif idx == 1:
            self.record_widget.show()
        elif idx == 2:
            self.history_task_widget.show()
        elif idx == 3:
            self.status_widget.show()
        elif idx == 4:
            self.monitor_widget.show()  # 新增
    def resizeEvent(self, event):
        w, h = self.width(), self.height()
        base = min(w, h)
        # 动态调整菜单栏宽度
        menu_width = max(100, min(220, int(w * 0.13)))
        self.menu_widget.setMinimumWidth(menu_width)
        self.menu_widget.setMaximumWidth(menu_width)
        font_size = max(8, int(base * 0.013))
        # LOGO字体更大
        logo_font = max(16, int(base * 0.025))
        for btn in self.menu_buttons:
            btn.setFont(QFont("Microsoft YaHei UI", font_size))
            btn.setFixedHeight(int(h * 0.045))
            # 同步按钮内icon和文字大小
            for j in range(btn.layout().count()):
                wgt = btn.layout().itemAt(j).widget()
                if isinstance(wgt, QLabel):
                    if j == 0:
                        wgt.setFont(QFont("Microsoft YaHei UI", int(font_size*1.4)))
                    else:
                        wgt.setFont(QFont("Microsoft YaHei UI", font_size))
        self.logo.setText(f"<span style='font-size:{logo_font}px;font-weight:bold;color:white;'>🤖 NLAutomate</span>")
        # 内容区响应式
        content_font = max(12, int(base * 0.018))
        input_height = int(h * 0.055)
        btn_height = int(h * 0.065)
        title_font = max(18, int(base * 0.03))
        self.task_title.setFont(QFont("Microsoft YaHei UI", title_font, QFont.Bold))
        self.task_name_label.setFont(QFont("Microsoft YaHei UI", content_font))
        self.task_desc_label.setFont(QFont("Microsoft YaHei UI", content_font))
        self.task_name_input.setFont(QFont("Microsoft YaHei UI", content_font))
        self.task_desc_input.setFont(QFont("Microsoft YaHei UI", content_font))
        self.task_deadline_label.setFont(QFont("Microsoft YaHei UI", content_font))
        self.task_deadline_input.setFont(QFont("Microsoft YaHei UI", content_font))
        self.task_name_input.setFixedHeight(input_height)
        self.task_desc_input.setFixedHeight(input_height)
        self.task_deadline_input.setFixedHeight(input_height)
        self.create_btn.setFont(QFont("Microsoft YaHei UI", content_font))
        self.create_btn.setFixedHeight(btn_height)
        # 卡片宽度自适应80%
        card_width = int(w * 0.8)
        self.create_task_widget.setFixedWidth(card_width)
        # 历史任务卡片宽度自适应80%
        history_card_width = int(w * 0.8)
        self.history_task_widget.setFixedWidth(history_card_width)
        # 历史任务卡片高度自适应80%
        history_card_height = int(self.height() * 0.8)
        self.history_task_widget.setMinimumHeight(history_card_height)
        self.history_task_widget.setMaximumHeight(history_card_height)
        # 运行状态卡片宽度自适应80%
        status_card_width = int(w * 0.8)
        self.status_widget.setFixedWidth(status_card_width)
        # 运行状态卡片高度自适应80%
        status_card_height = int(self.height() * 0.8)
        self.status_widget.setMinimumHeight(status_card_height)
        self.status_widget.setMaximumHeight(status_card_height)
        # 历史任务区响应式
        table_font = max(12, int(min(self.width(), self.height()) * 0.018))
        self.history_title.setFont(QFont("Microsoft YaHei UI", max(18, int(min(self.width(), self.height()) * 0.03)), QFont.Bold))
        self.history_table.setFont(QFont("Microsoft YaHei UI", table_font))
        self.history_table.horizontalHeader().setFont(QFont("Microsoft YaHei UI", table_font, QFont.Bold))
        row_height = int(self.height() * 0.06)
        for row in range(self.history_table.rowCount()):
            self.history_table.setRowHeight(row, row_height)
        # 运行状态区响应式
        status_table_font = max(12, int(min(self.width(), self.height()) * 0.018))
        self.status_title.setFont(QFont("Microsoft YaHei UI", max(18, int(min(self.width(), self.height()) * 0.03)), QFont.Bold))
        self.status_table.setFont(QFont("Microsoft YaHei UI", status_table_font))
        self.status_table.horizontalHeader().setFont(QFont("Microsoft YaHei UI", status_table_font, QFont.Bold))
        status_row_height = int(self.height() * 0.06)
        for row in range(self.status_table.rowCount()):
            self.status_table.setRowHeight(row, status_row_height)
        # 任务录迹卡片宽度自适应80%
        record_card_width = int(w * 0.8)
        self.record_widget.setFixedWidth(record_card_width)
        # 任务录迹区响应式
        record_title_font = max(18, int(min(self.width(), self.height()) * 0.03))
        self.record_title.setFont(QFont("Microsoft YaHei UI", record_title_font, QFont.Bold))
        self.record_desc.setFont(QFont("Microsoft YaHei UI", max(14, int(min(self.width(), self.height()) * 0.018))))
        self.start_record_btn.setFont(QFont("Microsoft YaHei UI", max(14, int(min(self.width(), self.height()) * 0.018))))
        self.stop_record_btn.setFont(QFont("Microsoft YaHei UI", max(14, int(min(self.width(), self.height()) * 0.018))))
        self.start_record_btn.setFixedHeight(int(h * 0.065))
        self.stop_record_btn.setFixedHeight(int(h * 0.065))
        # 界面监控卡片宽度自适应80%
        monitor_card_width = int(w * 0.8)
        self.monitor_widget.setFixedWidth(monitor_card_width)
        # 界面监控卡片高度自适应80%
        monitor_card_height = int(self.height() * 0.8)
        self.monitor_widget.setMinimumHeight(monitor_card_height)
        self.monitor_widget.setMaximumHeight(monitor_card_height)
        # 字体、按钮等同步设置
        monitor_title_font = max(18, int(base * 0.03))
        monitor_status_font = max(14, int(base * 0.022))
        monitor_btn_height = int(h * 0.065)
        monitor_btn_font = max(14, int(base * 0.018))
        if hasattr(self, 'monitor_title'):
            self.monitor_title.setFont(QFont("Microsoft YaHei UI", monitor_title_font, QFont.Bold))
        if hasattr(self, 'monitor_status'):
            self.monitor_status.setFont(QFont("Microsoft YaHei UI", monitor_status_font))
        if hasattr(self, 'monitor_template_path'):
            self.monitor_template_path.setFont(QFont("Microsoft YaHei UI", max(12, int(base * 0.015))))
        for btn in [getattr(self, 'monitor_start_btn', None), getattr(self, 'monitor_stop_btn', None), getattr(self, 'monitor_log_btn', None), getattr(self, 'monitor_select_btn', None)]:
            if btn:
                btn.setFont(QFont("Microsoft YaHei UI", monitor_btn_font))
                btn.setFixedHeight(monitor_btn_height)
        super().resizeEvent(event)
    def load_history_tasks_from_db(self):
        self.history_table.setRowCount(0)
        for task in self.task_manager.get_tasks():
            self.add_task_to_history_table_db(task)

    def task_name_exists(self, name):
        # 检查历史任务表
        for row in range(self.history_table.rowCount()):
            if self.history_table.item(row, 0).text().strip() == name.strip():
                return True
        # 检查录迹任务表
        for row in range(self.record_table.rowCount()):
            if self.record_table.item(row, 0).text().strip() == name.strip():
                return True
        return False

    def handle_create_task(self):
        name = self.task_name_input.text().strip()
        desc = self.task_desc_input.text().strip()
        deadline_dt = self.task_deadline_input.dateTime()
        deadline = deadline_dt.toString("yyyy-MM-dd HH:mm")
        from PyQt5.QtCore import QDateTime
        if not name:
            QMessageBox.warning(self, "提示", "任务名称不能为空！")
            return
        if self.task_name_exists(name):
            QMessageBox.warning(self, "提示", "任务名称已存在，请更换名称！")
            return
        # 截止时间校验
        if deadline_dt < QDateTime.currentDateTime():
            QMessageBox.warning(self, "提示", "截止时间不能早于当前时间！")
            return
        reply = QMessageBox.question(self, "确认创建", f"确定要创建任务：{name}？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            # 添加到数据库并刷新录迹表格
            record_task = self.task_manager.add_record_task(name, False, deadline)
            self.add_record_task_to_table(record_task)
            self.task_name_input.clear()
            self.task_desc_input.clear()

    def add_task_to_history_table_db(self, task):
        row = self.history_table.rowCount()
        self.history_table.insertRow(row)
        self.history_table.setItem(row, 0, QTableWidgetItem(task.name))
        self.history_table.setItem(row, 1, QTableWidgetItem(task.deadline))
        # 状态圆点（未开始-灰色，已完成-绿色，失败-红色）
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setAlignment(Qt.AlignCenter)
        status_label = QLabel()
        status_label.setFixedSize(24, 24)
        color = "#bdbdbd" if task.status == "未开始" else ("#4caf50" if task.status == "已完成" else "#f44336")
        status_label.setStyleSheet(f"border-radius:12px; background:{color};")
        status_layout.addWidget(status_label)
        status_widget.setStyleSheet("background: transparent;")
        self.history_table.setCellWidget(row, 2, status_widget)
        # 操作列-运行和删除按钮
        op_widget = QWidget()
        op_layout = QHBoxLayout(op_widget)
        op_layout.setContentsMargins(0, 0, 0, 0)
        op_layout.setAlignment(Qt.AlignCenter)
        run_btn = QPushButton("运行")
        run_btn.setStyleSheet('''
            QPushButton {
                min-width:32px; min-height:22px; border-radius:8px;
                background:#19e3e3; color:white; font-weight:bold;
                transition: all 0.18s;
            }
            QPushButton:hover {
                background:#0bbaba;
                color:white;
                box-shadow: 0 2px 8px 0 rgba(25,163,163,0.18);
            }
        ''')
        run_btn.clicked.connect(lambda _, tname=task.name: self.run_history_task(tname))
        del_btn = QPushButton("删除")
        del_btn.setStyleSheet('''
            QPushButton {
                min-width:32px; min-height:22px; border-radius:8px;
                background:#f44336; color:white; font-weight:bold;
                transition: all 0.18s;
            }
            QPushButton:hover {
                background:#c62828;
                color:white;
                box-shadow: 0 2px 8px 0 rgba(244,67,54,0.18);
            }
        ''')
        del_btn.clicked.connect(lambda _, r=row, tid=task.id: self.delete_history_task(r, tid))
        op_layout.addWidget(run_btn)
        op_layout.addWidget(del_btn)
        op_widget.setStyleSheet("background: transparent;")
        self.history_table.setCellWidget(row, 3, op_widget)
        self.history_table.setRowHeight(row, int(self.height() * 0.08))
        self.history_table.setVerticalHeaderItem(row, QTableWidgetItem(str(task.id)))

    def run_history_task(self, task_name):
        import os
        from recorder import Recorder
        import re
        from PyQt5.QtCore import QDateTime
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', task_name)
        filename = f"{safe_name}.json"
        if not os.path.exists(filename):
            QMessageBox.warning(self, "未找到录制文件", f"未找到对应的录制文件：{filename}")
            return
        # 检查截止时间
        task_row = None
        for row in range(self.history_table.rowCount()):
            if self.history_table.item(row, 0).text().strip() == task_name:
                task_row = row
                break
        if task_row is not None:
            deadline_str = self.history_table.item(task_row, 1).text()
            deadline_dt = QDateTime.fromString(deadline_str, "yyyy-MM-dd HH:mm")
            if deadline_dt.isValid() and deadline_dt < QDateTime.currentDateTime():
                QMessageBox.warning(self, "已到达截止时间", "该任务已超过截止时间，无法启动定时任务！")
                return
        dialog = RunConfigDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            run_time, repeat_count, repeat_interval = dialog.get_config()
            run_time_str = run_time.toString("HH:mm")
            schedule_id = self.task_manager.add_schedule_task(task_name, run_time_str, repeat_count, filename, "等待中")
            scheduler = TaskScheduler(task_name, run_time, repeat_count, filename, self)
            scheduler.db_id = schedule_id
            scheduler.repeat_interval = repeat_interval  # 新增：保存到scheduler对象
            # 传递截止时间
            if task_row is not None:
                deadline_str = self.history_table.item(task_row, 1).text()
                scheduler.deadline_str = deadline_str
            self.schedulers.append(scheduler)
            self.refresh_status_table()
            QMessageBox.information(self, "定时任务已启动", f"每天{run_time.toString('HH:mm')}自动执行，重复{repeat_count}次，间隔{repeat_interval}秒。\n可最小化窗口到后台。")

    def delete_history_task(self, row, task_id):
        task_name = self.history_table.item(row, 0).text().strip()
        import os, re
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', task_name)
        filename = f"{safe_name}.json"
        reply = QMessageBox.question(self, "确认删除", f"确定要删除该任务及其录制文件（{filename}）吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.task_manager.remove_task(task_id)
            self.history_table.removeRow(row)
            # 删除json文件，保证不会崩溃
            try:
                if os.path.exists(filename):
                    os.remove(filename)
            except Exception as e:
                QMessageBox.warning(self, "文件删除失败", f"录制文件删除失败：{e}")

    def load_record_tasks_from_db(self):
        self.record_table.setRowCount(0)
        for record_task in self.task_manager.get_record_tasks():
            self.add_record_task_to_table(record_task)

    def add_record_task_to_table(self, record_task):
        row = self.record_table.rowCount()
        self.record_table.insertRow(row)
        self.record_table.setItem(row, 0, QTableWidgetItem(record_task.name))
        is_record_str = "是" if record_task.is_record else "否"
        self.record_table.setItem(row, 1, QTableWidgetItem(is_record_str))
        self.record_table.setItem(row, 2, QTableWidgetItem(record_task.deadline))
        # 操作列-删除按钮
        op_widget = QWidget()
        op_layout = QHBoxLayout(op_widget)
        op_layout.setContentsMargins(0, 0, 0, 0)
        op_layout.setAlignment(Qt.AlignCenter)
        del_btn = QPushButton("删除")
        del_btn.setStyleSheet('''
            QPushButton {
                min-width:32px; min-height:22px; border-radius:8px;
                background:#f44336; color:white; font-weight:bold;
                transition: all 0.18s;
            }
            QPushButton:hover {
                background:#c62828;
                color:white;
                box-shadow: 0 2px 8px 0 rgba(244,67,54,0.18);
            }
        ''')
        def handle_del():
            btn = self.sender()
            # 获取按钮所在的单元格行号
            index = self.record_table.indexAt(btn.parent().pos())
            real_row = index.row()
            self.delete_record_task(real_row, record_task.id)
        del_btn.clicked.connect(handle_del)
        op_layout.addWidget(del_btn)
        op_widget.setStyleSheet("background: transparent;")
        self.record_table.setCellWidget(row, 3, op_widget)

    def delete_record_task(self, row, task_id):
        reply = QMessageBox.question(self, "确认删除", "确定要删除该录迹任务吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.task_manager.remove_record_task(task_id)
            self.record_table.removeRow(row)

    def handle_start_record(self):
        selected = self.record_table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "提示", "请先在任务录迹列表中选择一个任务！")
            return
        name = self.record_table.item(selected, 0).text().strip()
        # 新增：判断历史任务中是否有同名任务
        for row in range(self.history_table.rowCount()):
            if self.history_table.item(row, 0).text().strip() == name:
                QMessageBox.warning(self, "提示", f"历史任务中已存在同名任务：{name}，请先删除或更换名称！")
                return
        task_id = self.record_table.item(selected, 0).text()
        deadline = self.record_table.item(selected, 2).text()
        choice = QMessageBox.question(
            self, "选择录制类型", "是否录制鼠标移动轨迹？\n选择'是'录制轨迹，选择'否'只录制离散事件。",
            QMessageBox.Yes | QMessageBox.No
        )
        record_move = (choice == QMessageBox.Yes)
        self.current_record_task = {'id': task_id, 'name': name, 'deadline': deadline}
        self.recorder = Recorder(record_move=record_move)
        self.is_recording = True
        self.start_record_btn.setEnabled(False)
        self.stop_record_btn.setEnabled(True)
        self.record_table.selectRow(selected)
        # 录制前提醒
        reply = QMessageBox.question(self, "录制准备", "建议关闭其他程序以避免误操作。\n确认后点击OK开始录制。", QMessageBox.Ok | QMessageBox.Cancel)
        if reply != QMessageBox.Ok:
            self.is_recording = False
            self.start_record_btn.setEnabled(True)
            self.stop_record_btn.setEnabled(False)
            return
        self.hide()
        def stop_record_from_indicator():
            self.handle_stop_record()
            self.show()
        self.record_indicator = RecordIndicator(stop_record_from_indicator)
        screen = QApplication.primaryScreen().geometry()
        x = screen.right() - self.record_indicator.width() - 30
        y = screen.bottom() - self.record_indicator.height() - 30
        self.record_indicator.move(x, y)
        self.record_indicator.show()
        self.recorder.start_record()

    def handle_stop_record(self):
        if self.record_indicator:
            self.record_indicator.close()
            self.record_indicator = None
        if not self.current_record_task or not self.is_recording:
            return
        self.recorder.stop_record()
        self.is_recording = False
        task_name = self.current_record_task['name'].strip()
        import re
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', task_name)
        filename = f"{safe_name}.json"
        self.recorder.save_record(filename)
        QMessageBox.information(self, "录制完成", f"录制已保存为 {filename}")
        reply = QMessageBox.question(self, "录制完成", f'''是否将任务"{task_name}"保存到历史任务？''', QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            task = self.task_manager.add_task(
                self.current_record_task['name'],
                '',
                self.current_record_task['deadline'],
                status="已完成"
            )
            self.add_task_to_history_table_db(task)
        self.current_record_task = None
        self.start_record_btn.setEnabled(True)
        self.stop_record_btn.setEnabled(False)

    def refresh_status_table(self):
        self.status_table.setRowCount(0)
        if not hasattr(self, 'schedulers'):
            return
        btn_style = '''
        QPushButton {{
            min-width:32px; min-height:22px; border-radius:8px;
            background:{bg}; color:white; font-weight:bold;
            border:none;
            transition: all 0.18s;
        }}
        QPushButton:hover {{
            background:{bg_hover};
            color:white;
            box-shadow: 0 2px 8px 0 rgba({shadow});
        }}
        '''
        from PyQt5.QtCore import QDateTime
        for scheduler in self.schedulers:
            # 检查截止时间，若超过则强制暂停
            is_expired = False
            if hasattr(scheduler, 'deadline_str') and scheduler.deadline_str:
                deadline_dt = QDateTime.fromString(scheduler.deadline_str, "yyyy-MM-dd HH:mm")
                if deadline_dt.isValid() and deadline_dt < QDateTime.currentDateTime():
                    if not scheduler.paused:
                        scheduler.pause()
                    is_expired = True
                    scheduler.status = "超时"
                    if hasattr(scheduler, 'db_id') and scheduler.db_id is not None:
                        self.task_manager.update_schedule_status(scheduler.db_id, "超时")
            row = self.status_table.rowCount()
            self.status_table.insertRow(row)
            self.status_table.setItem(row, 0, QTableWidgetItem(scheduler.task_name))
            self.status_table.setItem(row, 1, QTableWidgetItem(scheduler.run_time.toString("HH:mm")))
            self.status_table.setItem(row, 2, QTableWidgetItem(str(scheduler.repeat_count)))
            self.status_table.setItem(row, 3, QTableWidgetItem(scheduler.next_run_time()))
            # 状态列：按钮逻辑根据status
            pause_widget = QWidget()
            pause_layout = QHBoxLayout(pause_widget)
            pause_layout.setContentsMargins(0, 0, 0, 0)
            pause_layout.setAlignment(Qt.AlignCenter)
            # 按status决定按钮文字
            if scheduler.status == "等待中":
                btn_pause = QPushButton("暂停")
                btn_pause.setStyleSheet(btn_style.format(
                    bg="#f44336", bg_hover="#c62828", shadow="244,67,54,0.18"
                ))
            else:  # "超时" 或 "暂停中"
                btn_pause = QPushButton("开始")
                btn_pause.setStyleSheet(btn_style.format(
                    bg="#4caf50", bg_hover="#388e3c", shadow="76,175,80,0.18"
                ))
            btn_pause.clicked.connect(partial(self.toggle_scheduler_pause, scheduler))
            pause_layout.addWidget(btn_pause)
            pause_widget.setStyleSheet("background: transparent;")
            self.status_table.setCellWidget(row, 4, pause_widget)
            # 操作列：删除按钮同理
            del_widget = QWidget()
            del_layout = QHBoxLayout(del_widget)
            del_layout.setContentsMargins(0, 0, 0, 0)
            del_layout.setAlignment(Qt.AlignCenter)
            del_btn = QPushButton("删除")
            del_btn.setStyleSheet(btn_style.format(
                bg="#f44336", bg_hover="#c62828", shadow="244,67,54,0.18"
            ))
            del_btn.clicked.connect(partial(self.remove_scheduler, scheduler))
            del_layout.addWidget(del_btn)
            del_widget.setStyleSheet("background: transparent;")
            self.status_table.setCellWidget(row, 5, del_widget)

    def toggle_scheduler_pause(self, scheduler):
        from PyQt5.QtCore import QDateTime
        try:
            if scheduler.status == "等待中":
                scheduler.status = "暂停中"
                scheduler.pause()
                if hasattr(scheduler, 'db_id') and scheduler.db_id is not None:
                    self.task_manager.update_schedule_status(scheduler.db_id, "暂停中")
            elif scheduler.status in ("暂停中", "超时"):
                if scheduler.status == "超时":
                    QMessageBox.warning(self, "已到达截止时间", f"任务【{scheduler.task_name}】已超过截止时间，无法恢复！")
                    return
                scheduler.status = "等待中"
                scheduler.resume()
                if hasattr(scheduler, 'db_id') and scheduler.db_id is not None:
                    self.task_manager.update_schedule_status(scheduler.db_id, "等待中")
            self.refresh_status_table()
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "错误", f"发生异常：{e}\n{traceback.format_exc()}")

    def remove_scheduler(self, scheduler):
        if hasattr(self, 'schedulers'):
            self.schedulers.remove(scheduler)
            scheduler.timer.stop()
            if hasattr(scheduler, 'db_id'):
                self.task_manager.remove_schedule_task(scheduler.db_id)
            self.refresh_status_table()

    def closeEvent(self, event):
        # 关闭时清空monitor_thresholds表
        self.task_manager.conn.execute('DELETE FROM monitor_thresholds')
        self.task_manager.conn.commit()
        super().closeEvent(event)

class LogViewerDialog(QDialog):
    def __init__(self, log_file='monitor_log.txt', parent=None):
        super().__init__(parent)
        self.setWindowTitle("监控日志")
        self.resize(600, 400)
        self.log_file = log_file
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_log)
        self.timer.start(1000)  # 每秒刷新一次
        self.refresh_log()

    def refresh_log(self):
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
        except Exception as e:
            log_content = f"日志读取失败：{e}"
        scrollbar = self.text_edit.verticalScrollBar()
        at_bottom = scrollbar.value() == scrollbar.maximum()
        self.text_edit.setPlainText(log_content)
        if at_bottom:
            scrollbar.setValue(scrollbar.maximum())

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei UI", 10))
    window = DashboardWindow()
    window.setGeometry(100, 100, 1200, 800)
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()