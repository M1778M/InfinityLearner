import json
from datetime import datetime, timedelta
import win32con
import win32gui
import sys
import ctypes
from ctypes import wintypes, CFUNCTYPE, POINTER, Structure, c_int, c_void_p
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import hashlib
import wmi
from PyQt6.QtWidgets import QProgressBar, QGraphicsOpacityEffect
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
# I hate chatgpt
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104  # like what the fuck is this

# ofcourse there is a CStruct in here
class KBDLLHOOKSTRUCT(Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

hook_id = None
hook_proc = None

#NOW HERE COMES MY TIME
class ConfigManager(QObject):
    #I hate chatgpt 2x
    dataChanged = pyqtSignal()
    
    def __init__(self, config_file='config.json'):
        super().__init__()
        self.config_file = config_file
        self.data = self.default_config()
        # Changed password to "lilbro" (it's literally useless because of line 554)
        self.data['settings']['admin_password'] = "3cf5d2e45f106ae553ed6afd8451eebd76a749a4428f8680431180d63e048c35"
        self.data['settings']['password_salt'] = "xlib" # Beingcool
        
        self.load_config()
        

    def default_config(self):
        """Returns a default configuration structure.""" # fr
        return {
    "lessons": {},
    "stats": {
        "points": 0,
        "started_date": str(datetime.now().date()),
        "predicted_end_date": None,
        "progress": [],
        "skipped_days": 0,
        "total_time_spent": 0,
        "consecutive_study_days": 0
    },
    "settings": {
        "max_skipped_days": 1,
        "strict_mode": True,
        "theme": "#34ff10",
        "scheduled_time": "18:00"
    },
    "rewards": {
                "history": [],
                "cooldowns": {},
                "5min_breaks": 3,
                "15min_breaks": 1,
                "extra_days": 1,
                "theme_color": "#2D2D2D"
            }
}

    def load_config(self):
        """Loads the configuration file. Creates a default one if it doesn't exist.""" # fr (2x)
        try:
            with open(self.config_file, 'r') as file:
                loaded_data = json.load(file)
                self.data = {**self.default_config(), **loaded_data}
        except (FileNotFoundError, json.JSONDecodeError):
            self.save_config()

    def save_config(self):
        """Saves the current configuration to the file.""" # fr (3x)
        with open(self.config_file, 'w') as file:
            json.dump(self.data, file, indent=4)
        self.dataChanged.emit()  # I hate emit funktion in every aspect (not just qt)

    def add_lesson(self, lesson_name, number_of_pages, study_pages_per_day):
        """Adds a new lesson to the configuration.""" # fr (4x)
        self.data['lessons'][lesson_name] = {
            "NumberOfPages": number_of_pages,
            "IsStudying": False,
            "StudyPagePerDay": study_pages_per_day,
            "CompletedPages": 0
        }
        self.save_config()

    def start_study(self, lesson_name):
        """Starts a study session for the specified lesson.""" # fr (5x)
        if lesson_name in self.data['lessons']:
            self.data['lessons'][lesson_name]['IsStudying'] = True # This is kinda useless too
            self.save_config()
        else:
            raise ValueError(f"Lesson '{lesson_name}' not found.")

    def end_study(self, lesson_name, time_spent):
        if lesson_name in self.data['lessons']:
            lesson = self.data['lessons'][lesson_name]
            points_earned = int((time_spent / 3600) * 100)  # Calculate points/money
            
            lesson['IsStudying'] = False
            lesson['CompletedPages'] += lesson['StudyPagePerDay']
            self.data['stats']['total_time_spent'] += time_spent
            self.data['stats']['progress'].append({ # Gotta study more...
                "Date": str(datetime.now().date()),
                "Lesson": lesson_name,
                "NumberOfPages": lesson['StudyPagePerDay'],
                "Skipped": False,
                "TimeFinished": time_spent,
                "PointsEarned": points_earned
            })
            self.update_points(time_spent)
            self.save_config()

    def update_points(self, time_spent):
        """Updates the user's points based on the time spent studying.""" # fr (6x)
        points_earned = int((time_spent / 3600) * 100)  # 100 points per hour (I NEED MORE)
        self.data['stats']['points'] += points_earned
        self.save_config()

    def skip_day(self):
        """Marks the current day as skipped and updates stats.""" # fr (7x)
        self.data['stats']['skipped_days'] += 1
        self.data['stats']['points'] -= 500  # Deduct points for skipping (PUNISHMENT) remember kids never skip school cause that shit deducts(whatever that means) your points
        self.data['stats']['progress'].append({
            "Date": str(datetime.now().date()),
            "Lesson": None,
            "NumberOfPages": 0,
            "Skipped": True,
            "TimeFinished": 0
        })
        self.save_config()

    def get_block_window(self):
        return SecureBlockWindow(self)

    def enforce_schedule(self, start_time, end_time):
        """Checks if the user has started their study within the scheduled timeframe.""" # fr (7x)
        now = datetime.now().time()
        if start_time <= now <= end_time: # Time to study
            print("Study session started.")
        else:
            self.block_user()

    def get_summary(self):
        """Returns a summary of the user's progress and stats.""" # fr (8x)
        return { # YOU SUCK
            "total_points": self.data['stats']['points'],
            "started_date": self.data['stats']['started_date'],
            "predicted_end_date": self.data['stats']['predicted_end_date'],
            "progress": self.data['stats']['progress'],
            "skipped_days": self.data['stats']['skipped_days'],
            "total_time_spent": self.data['stats']['total_time_spent'],
            "consecutive_study_days": self.data['stats']['consecutive_study_days']
        }

class SecureBlockWindow(QMainWindow): # LET ME COOK NOW...
    def __init__(self, config_manager):
        super().__init__()
        # OFCOURSE IT NEEDS A TURN
        self.keyboard_hook = None
        self.process_monitor = None
        self.focus_timer = QTimer()
        self.study_timer = QTimer()
        self.save_timer = QTimer()
        self.progress_anim = None
        self.color_anim = None
        self.time_effect = None
        self.current_lesson = None
        self.start_time = None
        self.remaining_time = 3600
        self.last_update = QDateTime.currentDateTime()
        try:
            self.config = config_manager
            self.setup_ui()
            self.setup_security()
            self.setup_timers()
            self.setup_animations()
            self.focus_timer.start(100)
        except Exception as e:
            print(f"Window initialization failed: {e}") #
            self.clean_exit()

    def setup_ui(self):
        self.setWindowTitle("Focus Mode - Infinity Learner")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                          Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        
        container = QWidget()
        container.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                      stop:0 #1a1a2e, stop:1 #16213e);
            color: white;
            border-radius: 15px;
        """)
        layout = QVBoxLayout()
        
        header = QLabel("🚀 Focus Mode Activated") #FR?
        header.setStyleSheet("""
            QLabel {
                font: bold 28px;
                padding: 20px;
                color: #e94560;
                qproperty-alignment: AlignCenter;
            }
        """)

        self.progress = QProgressBar()
        self.progress.setRange(0, 3600)
        self.progress.setValue(3600)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                height: 250px;
                width: 250px;
                min-width: 250px;
                max-width: 250px;
                min-height: 250px;
                max-height: 250px;
                border-radius: 125px;
                border: 5px solid #3d3d3d;
            }
            QProgressBar::chunk {
                background: qconicalgradient(cx:0.5, cy:0.5, angle:90,
                                           stop:0 #e94560, stop:1 #0f3460);
                border-radius: 125px;
            }
        """)

        self.time_label = QLabel("60:00")
        self.time_label.setStyleSheet("""
            QLabel {
                font: bold 48px;
                color: #e94560;
                qproperty-alignment: AlignCenter;
            }
        """)

        self.lesson_info = QLabel("No active lesson")
        self.lesson_info.setStyleSheet("""
            QLabel {
                font: 20px;
                color: #8f94fb;
                qproperty-alignment: AlignCenter;
                padding: 15px;
            }
        """)

        self.start_btn = QPushButton("▶ Start Session") # Bad button
        self.end_btn = QPushButton("⏹ End Session") # Good button
        self.end_btn.setEnabled(False)
        
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(20, 20)
        self.status_indicator.setStyleSheet("""
            QLabel {
                background-color: #e74c3c;
                border-radius: 10px;
            }
        """)

        button_style = """
            QPushButton {
                font: bold 18px;
                padding: 15px 30px;
                border-radius: 25px;
                min-width: 200px;
            }
            QPushButton:disabled {
                background: #95a5a6;
                color: #2c3e50;
            }
        """
        self.start_btn.setStyleSheet(button_style + """
            background: #4CAF50;
            color: white;
        """)
        self.end_btn.setStyleSheet(button_style + """
            background: #e74c3c;
            color: white;
        """)

        self.emergency_btn = QPushButton("🚨 Emergency Exit (Admin Required)") # I don't know the password lilbro
        self.emergency_btn.setObjectName("emergency-btn")
        self.emergency_btn.setStyleSheet("""
            QPushButton {
                background: #e94560;
                color: white;
                font: bold 14px;
                padding: 10px 20px;
                border-radius: 15px;
                margin-top: 30px;
            }
            QPushButton:hover {
                background: #d33f58;
            }
        """)

        center = QWidget()
        center_layout = QVBoxLayout()
        center_layout.addWidget(header)
        center_layout.addWidget(self.progress, 0, Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(self.time_label)
        center_layout.addWidget(self.lesson_info)
        
        button_container = QWidget()
        button_layout = QVBoxLayout()
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.end_btn)
        button_container.setLayout(button_layout)
        
        center_layout.addWidget(button_container, 0, Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(self.emergency_btn, 0, Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(self.status_indicator, 0, Qt.AlignmentFlag.AlignCenter)
        center.setLayout(center_layout)

        layout.addWidget(center, 0, Qt.AlignmentFlag.AlignCenter)
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.overlay = QWidget()
        self.overlay.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                                  Qt.WindowType.WindowStaysOnTopHint)
        self.overlay.setStyleSheet("background: rgba(0,0,0,0.7);")
        self.overlay.setWindowState(Qt.WindowState.WindowFullScreen)
        self.overlay.show()

        # Connect signals
        self.start_btn.clicked.connect(self.start_study)
        self.end_btn.clicked.connect(self.end_study)
        self.emergency_btn.clicked.connect(self.verify_emergency_exit)

    def setup_security(self): # Trust me I know how it works
        try:
            self.HOOKPROC = CFUNCTYPE(c_int, c_int, c_int, POINTER(c_void_p))
            self.keyboard_callback = self.HOOKPROC(self.keyboard_proc)
            self.keyboard_hook = ctypes.windll.user32.SetWindowsHookExA(
                WH_KEYBOARD_LL,
                self.keyboard_callback,
                ctypes.windll.kernel32.GetModuleHandleW(None),
                0
            )
            self.process_monitor = QTimer()
            self.process_monitor.timeout.connect(self.check_processes)
            self.process_monitor.start(1000)
        except Exception as e:
            print(f"Security setup failed: {e}")

    def check_processes(self):
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                if any(name in proc.info['name'].lower() for name in ['taskmgr', 'processhacker']): #HACKER?
                    try:
                        proc.kill()
                    except psutil.AccessDenied:
                        pass
        except Exception as e:
            print(f"Process monitor error: {e}")

    def setup_timers(self): # TIMERS ARE EVERYWHERE
        self.focus_timer = QTimer()
        self.focus_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.focus_timer.timeout.connect(self.keep_focus)
        
        self.study_timer = QTimer()
        self.study_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.study_timer.timeout.connect(self.update_timer)
        self.study_timer.start(100) 
        
        self.process_monitor = QTimer()
        self.process_monitor.timeout.connect(self.check_processes)
        self.process_monitor.start(5000)

    def setup_animations(self): # QT ANIMATIONS SUCK
        try:
            self.progress_anim = QPropertyAnimation(self.progress, b"value")
            self.progress_anim.setDuration(3600 * 1000)
            self.progress_anim.setStartValue(3600)
            self.progress_anim.setEndValue(0)
            
            self.time_effect = QGraphicsColorizeEffect()
            self.time_label.setGraphicsEffect(self.time_effect)
            self.color_anim = QPropertyAnimation(self.time_effect, b"color")
            self.color_anim.setDuration(1000)
            self.color_anim.setLoopCount(-1)
            self.color_anim.setStartValue(QColor("#e94560"))
            self.color_anim.setEndValue(QColor("#8f94fb"))
        except Exception as e:
            print(f"Animation setup error: {e}")

    def start_study(self): # Worst function of all time
        try:
            self.start_time = QDateTime.currentDateTime()
            self.start_btn.setEnabled(False)
            QApplication.processEvents()
            
            if self.study_timer.isActive():
                return

            self.start_time = QDateTime.currentDateTime()
            self.last_update = self.start_time
            self.study_timer.start(100) 
            
            # ANIMATIONS AGAIN?
            if self.progress_anim:
                self.progress_anim.stop()
                self.progress_anim.setStartValue(3600)
                self.progress_anim.setEndValue(0)
                self.progress_anim.setDuration(3600 * 1000)
                self.progress_anim.start()
            self.current_lesson = next(
                (name for name, lesson in self.config.data['lessons'].items() 
                 if lesson['IsStudying']), None
            )
            if not self.current_lesson:
                raise ValueError("No active lesson selected")
                
            self.start_btn.setEnabled(False)
            self.start_time = datetime.now()
            self.study_timer.start(1000)
            self.progress_anim.start()
            self.color_anim.start()
            self.update_lesson_info()
        except Exception as e:
            print(f"Failed to start session: {e}")
            self.start_btn.setEnabled(True)


    def end_study(self): # Best function ever
        try:
            if self.current_lesson and self.remaining_time <= 0:
                time_spent = (datetime.now() - self.start_time).total_seconds()
                self.config.end_study(self.current_lesson, int(time_spent))
                self.clean_exit()
        except Exception as e:
            print(f"Error ending session: {e}")
        finally:
            self.clean_exit()

    def update_timer(self):
        try:
            now = QDateTime.currentDateTime()
            if not self.start_time:
                return
            elapsed = self.start_time.msecsTo(now)
            
            if self.last_update.msecsTo(now) < 250:
                return
            self.remaining_time = max(0, 3600000 - elapsed) # #IHATESTUDYING

            if self.last_update.msecsTo(now) < 250:
                return
                
            self.last_update = now
            
            seconds = self.remaining_time // 1000
            mins, secs = divmod(seconds, 60)
            
            self.time_label.setText(f"{mins:02}:{secs:02}")
            self.progress.setValue(seconds)
            
            self.end_btn.setEnabled(seconds <= 0)
            
            if seconds % 5 == 0:
                self.update_status_indicator()
                self.update_lesson_info()

        except Exception as e:
            print(f"Timer update error: {e}")

    def update_status_indicator(self):
        style = """
            QLabel {
                background-color: %s;
                border-radius: 10px;
                %s
            }
        """ % (
            "#2ecc71" if self.remaining_time > 0 else "#f1c40f",
            "animation: pulse 1s infinite;" if self.remaining_time > 0 else ""
        )
        self.status_indicator.setStyleSheet(style)

    def update_lesson_info(self): # COOl
        if self.current_lesson:
            lesson = self.config.data['lessons'][self.current_lesson]
            info = f"""
                📖 {self.current_lesson}
                📄 Pages: {lesson['StudyPagePerDay']}/day
                ✅ Completed: {lesson['CompletedPages']}
                ⏳ Remaining: {lesson['NumberOfPages'] - lesson['CompletedPages']}
            """
            self.lesson_info.setText(info.strip().replace("    ", ""))

    def keep_focus(self):
        try:
            if not self.isActiveWindow():
                self.activateWindow()
            self.overlay.lower()
        except Exception as e:
            print(f"Focus error: {e}")

    def verify_emergency_exit(self):
        try:
            QApplication.processEvents()
            self.disable_security()
            
            password, ok = QInputDialog.getText(
                self, "Emergency Exit", 
                "Enter admin password:",
                QLineEdit.EchoMode.Password
            )
            #PASSWORD=lilbro
            if ok and hashlib.sha256(password.encode()).hexdigest() == "3cf5d2e45f106ae553ed6afd8451eebd76a749a4428f8680431180d63e048c35":
                self.clean_exit()
                return
            else:
                QMessageBox.warning(self, "Access Denied", 
                                   "Incorrect password!", QMessageBox.StandardButton.Ok)
        except Exception as e:
            print(f"Emergency exit error: {e}")
        finally:
            self.enable_security()
            self.activateWindow()

    def disable_security(self):
        try:
            if self.keyboard_hook:
                ctypes.windll.user32.UnhookWindowsHookEx(self.keyboard_hook)
            if self.process_monitor:
                self.process_monitor.stop()
            ctypes.windll.user32.BlockInput(False)
        except Exception as e:
            print(f"Security disable error: {e}")

    def enable_security(self): # Def can't bypass it with Win+R taskkill /f /im python.exe but what if it is an executable? Win+R taskkill /f /im name.exe
        try:
            self.keyboard_hook = ctypes.windll.user32.SetWindowsHookExA(
                WH_KEYBOARD_LL,
                self.keyboard_callback,
                ctypes.windll.kernel32.GetModuleHandleW(None),
                0
            )
            self.process_monitor.start(1000)
            ctypes.windll.user32.BlockInput(True)
        except Exception as e:
            print(f"Security enable error: {e}")

    def verify_password(self, input_password): # It doesn't work (not used)
        import hashlib
        salt = self.config.data['settings'].get('password_salt', '')
        stored_hash = self.config.data['settings'].get('admin_password', '')
        input_hash = hashlib.sha256((input_password + salt).encode()).hexdigest()
        return input_hash == stored_hash

    def clean_exit(self):
        try:
            self.process_monitor.stop()
            self.focus_timer.stop()
            self.study_timer.stop()
            self.save_timer.stop()
            
            if self.progress_anim:
                self.progress_anim.stop()
            if self.color_anim:
                self.color_anim.stop()
                
            if self.keyboard_hook:
                ctypes.windll.user32.UnhookWindowsHookEx(self.keyboard_hook)
                
            ctypes.windll.user32.BlockInput(False)
            self.overlay.close()
            self.close()
            
        except Exception as e:
            print(f"Clean exit error: {e}")
        finally:
            self.deleteLater()

    def closeEvent(self, event):
        if self.remaining_time > 0:
            self.verify_emergency_exit()
            event.ignore()
        else:
            self.clean_exit()
            event.accept()

    def keyboard_proc(self, nCode, wParam, lParam): # WHERE IS ELON MUSK???
        try:
            if nCode >= 0:
                kb_struct = ctypes.cast(lParam, POINTER(KBDLLHOOKSTRUCT)).contents
                if (wParam in (WM_KEYDOWN, WM_SYSKEYDOWN) and
                    kb_struct.vkCode == 0x4C and
                    ctypes.windll.user32.GetAsyncKeyState(win32con.VK_CONTROL) and
                    ctypes.windll.user32.GetAsyncKeyState(win32con.VK_MENU)):
                    self.verify_emergency_exit()
                    return 1
                    
                if self.should_block_key(kb_struct, wParam):
                    return 1
        except Exception as e:
            print(f"Keyboard hook error: {e}")
        finally:
            return ctypes.windll.user32.CallNextHookEx(self.keyboard_hook, nCode, wParam, lParam)

    def should_block_key(self, kb_struct, wParam): #ELON??!!
        return any([
            wParam in (WM_KEYDOWN, WM_SYSKEYDOWN) and (
                (kb_struct.vkCode == win32con.VK_TAB and 
                 ctypes.windll.user32.GetAsyncKeyState(win32con.VK_MENU)) or
                (kb_struct.vkCode == win32con.VK_F4 and 
                 ctypes.windll.user32.GetAsyncKeyState(win32con.VK_MENU)) or
                kb_struct.vkCode in (win32con.VK_LWIN, win32con.VK_RWIN)
            )
        ])


def study_session(config_manager): # Second worst function of all time
    """Main entry point for starting a study session"""
    app = QApplication(sys.argv)
    window = BlockWindow(config_manager)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__": # TEST OF COURSE
    # manager = ConfigManager()
    # manager.add_lesson("Math", 132, 25)
    # manager.start_study("Math")
    # manager.end_study("Math", 7200)
    # print(manager.get_summary())
    # manager.block_user()
    #I still hate studying
    print("Me too")
