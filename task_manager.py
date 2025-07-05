import sqlite3
import datetime

class Task:
    def __init__(self, name, desc, deadline, status="未开始", task_id=None):
        self.id = task_id
        self.name = name
        self.desc = desc
        self.deadline = deadline
        self.status = status

class RecordTask:
    def __init__(self, task_id, name, is_record, deadline, create_time):
        self.id = task_id
        self.name = name
        self.is_record = is_record
        self.deadline = deadline
        self.create_time = create_time

class TaskManager:
    def __init__(self, db_path="tasks.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self._create_table()
        self._create_record_table()
        self._create_schedule_table()
        self._create_monitor_threshold_table()

    def _create_table(self):
        c = self.conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                desc TEXT,
                deadline TEXT,
                status TEXT
            )
        ''')
        self.conn.commit()

    def _create_record_table(self):
        c = self.conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS record_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                is_record INTEGER DEFAULT 0,
                deadline TEXT,
                create_time TEXT
            )
        ''')
        self.conn.commit()

    def _create_schedule_table(self):
        c = self.conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS schedule_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT,
                run_time TEXT,
                repeat_count INTEGER,
                filename TEXT,
                status TEXT
            )
        ''')
        self.conn.commit()

    def _create_monitor_threshold_table(self):
        c = self.conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS monitor_thresholds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                template_path TEXT,
                min_threshold REAL,
                max_threshold REAL,
                create_time TEXT
            )
        ''')
        self.conn.commit()

    def add_task(self, name, desc, deadline, status="未开始"):
        c = self.conn.cursor()
        c.execute('INSERT INTO tasks (name, desc, deadline, status) VALUES (?, ?, ?, ?)',
                  (name, desc, deadline, status))
        self.conn.commit()
        task_id = c.lastrowid
        return Task(name, desc, deadline, status, task_id)

    def remove_task(self, task_id):
        c = self.conn.cursor()
        c.execute('DELETE FROM tasks WHERE id=?', (task_id,))
        self.conn.commit()

    def get_tasks(self):
        c = self.conn.cursor()
        c.execute('SELECT id, name, desc, deadline, status FROM tasks')
        rows = c.fetchall()
        return [Task(name, desc, deadline, status, task_id) for task_id, name, desc, deadline, status in rows]

    def clear(self):
        c = self.conn.cursor()
        c.execute('DELETE FROM tasks')
        self.conn.commit()

    # 录迹任务相关
    def add_record_task(self, name, is_record, deadline):
        c = self.conn.cursor()
        create_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute('INSERT INTO record_tasks (name, is_record, deadline, create_time) VALUES (?, ?, ?, ?)',
                  (name, int(is_record), deadline, create_time))
        self.conn.commit()
        task_id = c.lastrowid
        return RecordTask(task_id, name, is_record, deadline, create_time)

    def remove_record_task(self, task_id):
        c = self.conn.cursor()
        c.execute('DELETE FROM record_tasks WHERE id=?', (task_id,))
        self.conn.commit()

    def get_record_tasks(self):
        c = self.conn.cursor()
        c.execute('SELECT id, name, is_record, deadline, create_time FROM record_tasks')
        rows = c.fetchall()
        return [RecordTask(task_id, name, is_record, deadline, create_time) for task_id, name, is_record, deadline, create_time in rows]

    def add_schedule_task(self, task_name, run_time, repeat_count, filename, status="等待中"):
        c = self.conn.cursor()
        c.execute('INSERT INTO schedule_tasks (task_name, run_time, repeat_count, filename, status) VALUES (?, ?, ?, ?, ?)',
                  (task_name, run_time, repeat_count, filename, status))
        self.conn.commit()
        return c.lastrowid

    def remove_schedule_task(self, schedule_id):
        c = self.conn.cursor()
        c.execute('DELETE FROM schedule_tasks WHERE id=?', (schedule_id,))
        self.conn.commit()

    def get_schedule_tasks(self):
        c = self.conn.cursor()
        c.execute('SELECT id, task_name, run_time, repeat_count, filename, status FROM schedule_tasks')
        rows = c.fetchall()
        return rows

    def update_schedule_status(self, schedule_id, status):
        c = self.conn.cursor()
        c.execute('UPDATE schedule_tasks SET status=? WHERE id=?', (status, schedule_id))
        self.conn.commit()

    def add_monitor_threshold(self, name, template_path, min_threshold=None, max_threshold=None):
        c = self.conn.cursor()
        create_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute('INSERT INTO monitor_thresholds (name, template_path, min_threshold, max_threshold, create_time) VALUES (?, ?, ?, ?, ?)',
                  (name, template_path, min_threshold, max_threshold, create_time))
        self.conn.commit()
        return c.lastrowid

    def update_monitor_threshold(self, threshold_id, min_threshold=None, max_threshold=None, template_path=None):
        c = self.conn.cursor()
        sql = 'UPDATE monitor_thresholds SET '
        params = []
        if min_threshold is not None:
            sql += 'min_threshold=?, '
            params.append(min_threshold)
        if max_threshold is not None:
            sql += 'max_threshold=?, '
            params.append(max_threshold)
        if template_path is not None:
            sql += 'template_path=?, '
            params.append(template_path)
        sql = sql.rstrip(', ') + ' WHERE id=?'
        params.append(threshold_id)
        c.execute(sql, tuple(params))
        self.conn.commit()

    def get_monitor_thresholds(self):
        c = self.conn.cursor()
        c.execute('SELECT id, name, template_path, min_threshold, max_threshold, create_time FROM monitor_thresholds')
        return c.fetchall()

    def remove_monitor_threshold(self, threshold_id):
        c = self.conn.cursor()
        c.execute('DELETE FROM monitor_thresholds WHERE id=?', (threshold_id,))
        self.conn.commit()