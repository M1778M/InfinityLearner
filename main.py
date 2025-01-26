import sys
import os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtCharts import QChart, QChartView, QPieSeries
from core_man import ConfigManager,SecureBlockWindow  
from progress import ProgressTab
from lesson_manager import LessonManager
from assistant import AssistantTab
import psutil
from pathlib import Path

def nice_path(pj):
    return str(Path(__file__).joinpath('..').joinpath(pj).absolute())

class CalendarWidget(QCalendarWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        self.setGridVisible(True)
        
    def paintCell(self, painter, rect, date):
        super().paintCell(painter, rect, date)
        date_str = date.toString("yyyy-MM-dd")
        
        for entry in self.config.data['stats']['progress']:
            if entry['Date'] == date_str:
                color = QColor(Qt.GlobalColor.green) if not entry['Skipped'] else QColor(Qt.GlobalColor.red)
                painter.fillRect(rect, color)
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(date.day()))
                return
            
class EnhancedCalendar(QCalendarWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        self.setGridVisible(True)
        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.setStyleSheet("""
            QCalendarWidget {
                background-color: #2c3e50;
                color: white;
                font-size: 14px;
            }
            QCalendarWidget QToolButton {
                height: 30px;
                width: 100px;
                color: white;
                font-size: 16px;
                icon-size: 24px;
            }
            QCalendarWidget QMenu {
                background-color: #34495e;
                color: white;
            }
        """)
        self.progress_data = self.process_progress_data()
        
        self.setWeekdayTextFormat(Qt.DayOfWeek.Sunday, QTextCharFormat())
        self.setWeekdayTextFormat(Qt.DayOfWeek.Saturday, QTextCharFormat())

    def process_progress_data(self):
        progress_data = {}
        for entry in self.config.data['stats']['progress']:
            date_str = entry['Date']
            if date_str not in progress_data:
                progress_data[date_str] = {
                    'studied': 0,
                    'skipped': 0,
                    'total_pages': 0,
                    'total_time': 0,
                    'lessons': set()
                }
            if entry['Skipped']:
                progress_data[date_str]['skipped'] += 1
            else:
                progress_data[date_str]['studied'] += 1
                progress_data[date_str]['total_pages'] += entry['NumberOfPages']
                progress_data[date_str]['total_time'] += entry['TimeFinished']
                if entry['Lesson']:
                    progress_data[date_str]['lessons'].add(entry['Lesson'])
        return progress_data

    def paintCell(self, painter, rect, date):
        super().paintCell(painter, rect, date)
        date_str = date.toString("yyyy-MM-dd")
        progress = self.progress_data.get(date_str)
        
        if progress:
            total_activities = progress['studied'] + progress['skipped']
            productivity = progress['studied'] / total_activities if total_activities else 0
            
            gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
            if progress['skipped'] > 0:
                gradient.setColorAt(0, QColor(231, 76, 60))
                gradient.setColorAt(1, QColor(192, 57, 43))
            else:
                hue = 120 * productivity  # Green (120°) to yellow (60°)
                color = QColor.fromHsl(hue, 255, 128)
                gradient.setColorAt(0, color.darker(120))
                gradient.setColorAt(1, color.lighter(120))

            painter.fillRect(rect, gradient)
            
            painter.setPen(QColor(255, 255, 255))
            text = f"{date.day()}\n"
            if progress['studied'] > 0:
                text += f"📖{progress['total_pages']}pgs\n⏱{progress['total_time']//3600}h"
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def event(self, event):
        """Add tooltip functionality"""
        if event.type() == QEvent.Type.ToolTip:
            date = self.dateAt(event.pos())
            date_str = date.toString("yyyy-MM-dd")
            progress = self.progress_data.get(date_str)
            if progress:
                tooltip = f"📅 {date_str}\n"
                tooltip += f"✅ Completed sessions: {progress['studied']}\n"
                tooltip += f"⏭ Skipped sessions: {progress['skipped']}\n"
                tooltip += f"📚 Lessons: {', '.join(progress['lessons']) or 'None'}"
                QToolTip.showText(event.globalPos(), tooltip, self)
        return super().event(event)

class InteractiveStatsGraph(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        self.figure = Figure(figsize=(10, 6), tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        # Interactive controls
        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["Daily", "Weekly", "Monthly"])
        self.interval_combo.currentIndexChanged.connect(self.update_graph)
        
        self.metric_combo = QComboBox()
        self.metric_combo.addItems(["Pages", "Time", "Points"])
        self.metric_mapping = {
            "Pages": "pages",
            "Time": "time", 
            "Points": "points"
        }
        
        layout = QVBoxLayout()
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("View:"))
        control_layout.addWidget(self.interval_combo)
        control_layout.addWidget(QLabel("Metric:"))
        control_layout.addWidget(self.metric_combo)
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        
        self.update_graph()

    def update_graph(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # Aggregate data based on selected interval
        interval = self.interval_combo.currentText()
        metric = self.metric_combo.currentText()
        metric_key = self.metric_mapping[metric]
        
        data = {}
        for entry in self.config.data['stats']['progress']:
            if entry['Skipped']:
                continue
                
            date = datetime.strptime(entry['Date'], "%Y-%m-%d")
            key = self._get_interval_key(date, interval)
            
            if key not in data:
                data[key] = {'pages': 0, 'time': 0, 'points': 0}
            
            data[key]['pages'] += entry['NumberOfPages']
            data[key]['time'] += entry['TimeFinished'] / 3600  # Hours
            data[key]['points'] += entry.get('PointsEarned', 0)
            
        dates = sorted(data.keys())
        metric_key = self.metric_mapping[metric]
        values = [data[d][metric_key] for d in dates]
        
        plt.style.use('seaborn')
        self.figure.set_facecolor('#f5f6fa')
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#f5f6fa')
        
        if interval == "Daily":
            bars = ax.bar(dates, values, color='#2ecc71', edgecolor='#27ae60')
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}', ha='center', va='bottom')
        else:
            line = ax.plot(dates, values, marker='o', linestyle='-', 
                          color='#3498db', markersize=8, linewidth=2)
            # Add data point annotations
            for x, y in zip(dates, values):
                ax.text(x, y, f'{y:.1f}', ha='right', va='bottom')

        ax.set_xlabel(interval, fontsize=12, labelpad=10)
        ax.set_ylabel(metric, fontsize=12, labelpad=10)
        ax.set_title(f"{metric} by {interval}", fontsize=14, pad=20)
        
        # Format dates
        if interval == "Daily":
            ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%d %b'))
        elif interval == "Weekly":
            ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
            
        ax.grid(True, linestyle='--', alpha=0.7)
        self.canvas.draw()

    def _get_interval_key(self, date, interval):
        if interval == "Daily":
            return date.date()
        elif interval == "Weekly":
            return date.isocalendar()[1]  # Week number
        elif interval == "Monthly":
            return date.replace(day=1).date()
        return date.date()
    
class InteractiveCalendar(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        self.selected_date = QDate.currentDate()
        self.setup_ui()
        self.setup_connections()
        self.load_theme()
        self.config.dataChanged.connect(self.update_calendar)

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #34495e; margin: 15px 0;")
        
        # Header with navigation and month overview
        self.header = QWidget()
        header_layout = QHBoxLayout()
        
        self.nav_buttons = QWidget()
        nav_layout = QHBoxLayout()
        self.prev_month_btn = self.create_nav_button("◀")
        self.next_month_btn = self.create_nav_button("▶")
        nav_layout.addWidget(self.prev_month_btn)
        nav_layout.addWidget(self.next_month_btn)
        self.nav_buttons.setLayout(nav_layout)
        
        self.month_header = QLabel()
        self.month_header.setStyleSheet("""
    QLabel {
        font-size: 20px;    // Reduced from 24px
        font-weight: bold;
        color: #3498db;
        margin: 5px 0;      // Reduced margin
        padding: 5px;
    }
""")
        self.month_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header_layout.addWidget(self.nav_buttons)
        header_layout.addWidget(self.month_header)
        header_layout.addStretch()
        
        self.header.setLayout(header_layout)
        
        # Calendar grid
        self.calendar_grid = QGridLayout()
        # In setup_ui method
        self.calendar_grid.setHorizontalSpacing(10)  # Changed from 8
        self.calendar_grid.setVerticalSpacing(10)    # Changed from 8
        self.calendar_grid.setContentsMargins(10, 10, 10, 10)
        self.setup_day_headers()
        
        # Progress overview
        self.progress_overview = QLabel()
        self.progress_overview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # In setup_ui method:
        calendar_container = QWidget()
        calendar_container.setLayout(QVBoxLayout())
        calendar_container.layout().setContentsMargins(10, 10, 10, 10)
        calendar_container.layout().addLayout(self.calendar_grid)
        
        
        main_layout.addWidget(self.header)
        main_layout.addWidget(calendar_container)
        main_layout.addWidget(separator)
        main_layout.addWidget(self.progress_overview)
        main_layout.setStretchFactor(calendar_container, 3)
        main_layout.setStretchFactor(self.progress_overview, 1)
        self.setLayout(main_layout)
        
        self.update_calendar()

    def create_nav_button(self, text):
        btn = QPushButton(text)
        btn.setFixedSize(40, 30)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def setup_day_headers(self):
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for col, name in enumerate(day_names):
            label = QLabel(name)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    color: #3498db;
                    padding: 5px;
                    border-bottom: 2px solid #3498db;
                }
            """)
            self.calendar_grid.addWidget(label, 0, col)

    def setup_connections(self):
        self.prev_month_btn.clicked.connect(self.prev_month)
        self.next_month_btn.clicked.connect(self.next_month)
    def prev_month(self):
        self.selected_date = self.selected_date.addMonths(-1)
        self.update_calendar()

    def next_month(self):
        self.selected_date = self.selected_date.addMonths(1)
        self.update_calendar()

    def load_theme(self):
        theme_color = self.config.data['rewards'].get('theme_color', '#2c3e50')
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {QColor(theme_color).darker(200).name()};
                color: {QColor(theme_color).lighter(150).name()};
                font-family: 'Segoe UI';
            }}
            QPushButton {{
                border: none;
                border-radius: 5px;
                padding: 5px;
                background-color: {QColor(theme_color).lighter(50).name()};
            }}
            QPushButton:hover {{
                background-color: {QColor(theme_color).lighter(100).name()};
            }}
        """)

    def update_calendar(self):
        # Remove fade animations causing errors
        self.clear_calendar_grid()
        self.month_header.setText(self.selected_date.toString("MMMM yyyy"))
        self.populate_days()
        self.update_progress_overview()
    
    def clear_calendar_grid(self):
        for i in reversed(range(self.calendar_grid.count())):
            widget = self.calendar_grid.itemAt(i).widget()
            if widget and i >= 7:  # Skip day headers
                widget.deleteLater()

    def populate_days(self):
        date = QDate(self.selected_date.year(), self.selected_date.month(), 1)
        row = 1
        col = date.dayOfWeek() - 1
        
        while date.month() == self.selected_date.month():
            day_btn = AnimatedDateButton(date)
            day_btn.clicked.connect(lambda _, d=date: self.show_date_menu(d))
            self.style_day_button(day_btn)
            self.calendar_grid.addWidget(day_btn, row, col)
            
            col += 1
            if col > 6:
                col = 0
                row += 1
            
            date = date.addDays(1)

    def style_day_button(self, button):
        date = button.date
        progress = self.get_date_progress(date.toString("yyyy-MM-dd"))
        theme_color = self.config.data['rewards'].get('theme_color', '#2c3e50')
        
        # Current day detection
        is_today = date == QDate.currentDate()
        
        style = f"""
            QPushButton {{
                background-color: {self.get_day_color(progress, theme_color)};
                color: white;
                font-weight: bold;
                min-width: 50px;
                min-height: 50px;
                border: 2px solid {QColor(theme_color).lighter(100).name()};
                font-size: 14px;
                padding: 5px;
        """

        # Add current day highlight
        if is_today:
            style += """
                border: 2px solid #f1c40f !important;
                background-color: rgba(241, 196, 15, 0.3);
            """
        
        style += """
            }
            QPushButton:hover {
                border-color: #f1c40f;
            }
        """
        
        button.setStyleSheet(style)
        button.setToolTip(self.create_tooltip(date, progress))
    def get_day_color(self, progress, theme_color):
        if progress['studied']:
            return "#27ae60"
        if progress['skipped']:
            return "#e74c3c"
        return QColor(theme_color).lighter(50).name()

    def get_hover_color(self, progress, theme_color):
        if progress['studied']:
            return "#219a52"
        if progress['skipped']:
            return "#c0392b"
        return QColor(theme_color).lighter(100).name()

    def create_tooltip(self, date, progress):
        tooltip = f"<b>{date.toString('MMMM d, yyyy')}</b>"
        if progress['studied']:
            tooltip += "<br>📚 Studied:"
            for entry in progress['entries']:
                tooltip += f"<br>• {entry['Lesson']}: {entry['Pages']} pages ({entry['Time']//3600}h)"
        elif progress['skipped']:
            tooltip += "<br>⏭ Skipped day"
        else:
            tooltip += "<br>📅 No study data"
        return tooltip

    def show_date_menu(self, date):
        menu = QMenu(self)
        progress = self.get_date_progress(date.toString("yyyy-MM-dd"))
        
        if progress['studied']:
            menu.addAction("📖 Edit Study Data", lambda: self.edit_study_data(date))
            menu.addAction("❌ Remove Study Data", lambda: self.remove_study_data(date))
        elif progress['skipped']:
            menu.addAction("✅ Unskip Day", lambda: self.unskip_day(date))
        else:
            menu.addAction("✅ Mark as Studied", lambda: self.mark_studied(date))
            menu.addAction("⏭ Mark as Skipped", lambda: self.mark_skipped(date))
        
        menu.addSeparator()
        menu.addAction("📅 Go to Today", self.go_to_today)
        menu.exec(QCursor.pos())

    def mark_studied(self, date):
        """Handles existing entries before creating new ones"""
        date_str = date.toString("yyyy-MM-dd")
        
        # Remove any existing entries
        self.config.data['stats']['progress'] = [
            entry for entry in self.config.data['stats']['progress']
            if entry['Date'] != date_str
        ]
        
        dialog = StudyEntryDialog(self.config, date, self)
        if dialog.exec():
            # Force immediate update
            self.config.save_config()
            self.config.dataChanged.emit()  # Add this line
            self.update_calendar()
    def get_date_progress(self, date_str):
        progress = {
            'studied': False,
            'skipped': False,
            'entries': [],
            'total_pages': 0,
            'total_time': 0
        }
        
        for entry in self.config.data['stats']['progress']:
            if entry['Date'] == date_str:
                if entry['Skipped']:
                    progress['skipped'] = True
                else:
                    progress['studied'] = True
                    progress['entries'].append({
                        'Lesson': entry['Lesson'],
                        'Pages': entry['NumberOfPages'],
                        'Time': entry['TimeFinished']
                    })
                    progress['total_pages'] += entry['NumberOfPages']
                    progress['total_time'] += entry['TimeFinished']
        
        # Ensure only one status is shown
        if progress['skipped']:
            progress['studied'] = False
        elif progress['studied']:
            progress['skipped'] = False
            
        return progress
    def update_progress_overview(self):
        """Updates the monthly progress summary at the bottom of the calendar"""
        month_start = QDate(self.selected_date.year(), self.selected_date.month(), 1)
        total_days = month_start.daysInMonth()
        studied_days = 0
        total_pages = 0
        total_time = 0

        current_date = month_start
        while current_date.month() == self.selected_date.month():
            date_str = current_date.toString("yyyy-MM-dd")
            progress = self.get_date_progress(date_str)
            
            if progress['studied']:
                studied_days += 1
                total_pages += progress['total_pages']
                total_time += progress['total_time']
            
            current_date = current_date.addDays(1)

        theme_color = self.config.data['rewards'].get('theme_color', '#2c3e50')
        text = f"""
<div style='
    border: 2px solid {theme_color}; 
    border-radius: 10px; 
    padding: 15px;
    margin: 15px 0;
    background: {QColor(theme_color).darker(150).name()};
'>
    <h3 style='color: #3498db; margin: 0 0 10px 0; font-size: 16px;'>
        {self.selected_date.toString("MMMM yyyy")} Summary
    </h3>
    <div style='font-size: 13px; line-height: 1.6;'>
        📅 <b>Studied Days:</b> {studied_days}/{total_days}<br>
        📚 <b>Total Pages:</b> {total_pages}<br>
        ⏱ <b>Study Time:</b> {total_time//3600}h {total_time%3600//60}m
    </div>
</div>
"""
        self.progress_overview.setText(text)
    def edit_study_data(self, date):
        dialog = StudyEntryDialog(self.config, date, self, edit_mode=True)
        if dialog.exec():
            self.config.save_config()
            self.update_calendar()

    def remove_study_data(self, date):
        date_str = date.toString("yyyy-MM-dd")
        self.config.data['stats']['progress'] = [
            entry for entry in self.config.data['stats']['progress']
            if entry['Date'] != date_str
        ]
        self.config.save_config()
        self.update_calendar()
    def _complete_calendar_update(self):
        # Actual update logic
        self.clear_calendar_grid()
        self.month_header.setText(self.selected_date.toString("MMMM yyyy"))
        self.populate_days()
        
        # Fade in animation
        fade_in = QPropertyAnimation(self.calendar_grid.parentWidget(), b"opacity")
        fade_in.setDuration(300)
        fade_in.setStartValue(0)
        fade_in.setEndValue(1)
        fade_in.start()
        
        self.update_progress_overview()
    
    def go_to_today(self):
        """Jumps to the current date and updates the calendar"""
        self.selected_date = QDate.currentDate()
        self.update_calendar()
    def unskip_day(self, date):
        """Removes skipped status from a date"""
        date_str = date.toString("yyyy-MM-dd")
        
        # Remove all skipped entries for this date
        self.config.data['stats']['progress'] = [
            entry for entry in self.config.data['stats']['progress']
            if entry['Date'] != date_str or not entry['Skipped']
        ]
        
        self.config.save_config()
        self.update_calendar()
    # Rest of the class remains the same with previous functionality...
    def mark_skipped(self, date):
        """Marks a date as skipped in the progress data"""
        date_str = date.toString("yyyy-MM-dd")
        
        # Remove any existing entries for this date
        self.config.data['stats']['progress'] = [
            entry for entry in self.config.data['stats']['progress']
            if entry['Date'] != date_str
        ]
        
        # Add new skipped entry
        self.config.data['stats']['progress'].append({
            "Date": date_str,
            "Lesson": None,
            "NumberOfPages": 0,
            "Skipped": True,
            "TimeFinished": 0
        })
        
        # Force immediate update
        self.config.save_config()
        self.config.dataChanged.emit()  # Add this line
        self.update_calendar()
class AnimatedDateButton(QPushButton):
    def __init__(self, date):
        super().__init__(str(date.day()))
        self.date = date
        self.effect = QGraphicsColorizeEffect()
        self.effect.setColor(QColor(46, 204, 113))
        self.setGraphicsEffect(self.effect)
        self.effect.setEnabled(False)
        
        self.animations = {
            'hover': QPropertyAnimation(self, b"geometry"),
            'click': QPropertyAnimation(self.effect, b"strength")
        }
        
        # Hover animation
        self.animations['hover'].setDuration(200)
        
        # Click animation
        self.animations['click'].setDuration(500)
        self.animations['click'].setKeyValueAt(0, 0)
        self.animations['click'].setKeyValueAt(0.5, 1)
        self.animations['click'].setKeyValueAt(1, 0)

    def enterEvent(self, event):
        self.animations['hover'].stop()
        self.animations['hover'].setStartValue(self.geometry())
        self.animations['hover'].setEndValue(self.geometry().adjusted(-1, -1, 2, 2))
        self.animations['hover'].start()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.animations['hover'].stop()
        self.animations['hover'].setStartValue(self.geometry())
        self.animations['hover'].setEndValue(self.geometry().adjusted(1, 1, -2, -2))
        self.animations['hover'].start()
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        self.effect.setEnabled(True)
        self.animations['click'].start()
        super().mousePressEvent(event)
class StudyEntryDialog(QDialog):
    def __init__(self, config, date, parent=None, edit_mode=False):
        super().__init__(parent)
        self.config = config
        self.date = date
        self.edit_mode = edit_mode
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Study Entry" + (" (Edit)" if self.edit_mode else ""))
        layout = QFormLayout()
        
        self.lesson_combo = QComboBox()
        self.lesson_combo.addItems([name for name in self.config.data['lessons'].keys()])
        
        self.pages_spin = QSpinBox()
        self.pages_spin.setRange(1, 1000)
        
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime(1, 0))  # Default 1 hour
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate_and_save)
        buttons.rejected.connect(self.reject)
        
        layout.addRow("Lesson:", self.lesson_combo)
        layout.addRow("Pages Studied:", self.pages_spin)
        layout.addRow("Study Duration:", self.time_edit)
        layout.addRow(buttons)
        
        if self.edit_mode:
            self.load_existing_data()
        
        self.setLayout(layout)
        
    def load_existing_data(self):
        date_str = self.date.toString("yyyy-MM-dd")
        entries = [e for e in self.config.data['stats']['progress'] 
                  if e['Date'] == date_str and not e['Skipped']]
        
        if entries:
            entry = entries[0]
            self.lesson_combo.setCurrentText(entry['Lesson'])
            self.pages_spin.setValue(entry['NumberOfPages'])
            total_seconds = entry['TimeFinished']
            self.time_edit.setTime(QTime(total_seconds//3600, (total_seconds%3600)//60))

    def validate_and_save(self):
        lesson = self.lesson_combo.currentText()
        pages = self.pages_spin.value()
        time = self.time_edit.time()
        total_seconds = time.hour() * 3600 + time.minute() * 60
        
        # Remove existing entries if editing
        if self.edit_mode:
            self.config.data['stats']['progress'] = [
                e for e in self.config.data['stats']['progress']
                if e['Date'] != self.date.toString("yyyy-MM-dd")
            ]
            
        self.config.data['stats']['progress'].append({
            "Date": self.date.toString("yyyy-MM-dd"),
            "Lesson": lesson,
            "NumberOfPages": pages,
            "Skipped": False,
            "TimeFinished": total_seconds,
            "PointsEarned": total_seconds // 3600 * 100
        })
        
        self.accept()

class EnhancedCreateProgramTab(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        self.setup_ui()
        self.setStyleSheet("""
            QLineEdit { 
                padding: 10px;
                font-size: 14px;
                min-width: 200px;
            }
            QSpinBox, QDateEdit {
                padding: 8px;
                min-width: 150px;
                max-width: 200px;
            }
            QLabel {
                font-size: 14px;
                margin-bottom: 5px;
            }
        """)

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(25)
        
        # Header
        header = QLabel("Create New Learning Plan")
        header.setStyleSheet("""
            font-size: 24px; 
            color: #2c3e50; 
            font-weight: bold;
            margin-bottom: 20px;
        """)
        main_layout.addWidget(header)
        
        # Content Container
        content_layout = QHBoxLayout()
        content_layout.setSpacing(30)
        
        # Form Column
        form_column = QVBoxLayout()
        form_column.setSpacing(15)
        
        # Lesson Name Section
        name_layout = QVBoxLayout()
        name_layout.addWidget(QLabel("Lesson Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter lesson name...")
        self.name_validator = QLabel()
        self.name_validator.setFixedSize(20, 20)
        
        name_input_layout = QHBoxLayout()
        name_input_layout.addWidget(self.name_edit)
        name_input_layout.addWidget(self.name_validator)
        name_input_layout.setSpacing(10)
        
        name_layout.addLayout(name_input_layout)
        form_column.addLayout(name_layout)
        
        # Pages Section
        pages_layout = QVBoxLayout()
        pages_layout.addWidget(QLabel("Pages:"))
        
        pages_input_layout = QHBoxLayout()
        pages_input_layout.setSpacing(15)
        
        total_layout = QVBoxLayout()
        total_layout.addWidget(QLabel("Total"))
        self.pages_spin = QSpinBox()
        self.pages_spin.setRange(10, 1000)
        self.pages_spin.setSingleStep(10)
        self.pages_spin.setMinimumSize(10,30)
        total_layout.addWidget(self.pages_spin)
        
        daily_layout = QVBoxLayout()
        daily_layout.addWidget(QLabel("Daily"))
        self.daily_spin = QSpinBox()
        self.daily_spin.setRange(1, 100)
        self.daily_spin.setMinimumSize(10,30)
        daily_layout.addWidget(self.daily_spin)
        
        pages_input_layout.addLayout(total_layout)
        pages_input_layout.addLayout(daily_layout)
        pages_layout.addLayout(pages_input_layout)
        form_column.addLayout(pages_layout)
        
        # Date Section
        date_layout = QVBoxLayout()
        date_layout.addWidget(QLabel("Target Date:"))
        self.duration_edit = QDateEdit()
        self.duration_edit.setDate(QDate.currentDate().addMonths(1))
        self.duration_edit.setCalendarPopup(True)
        self.duration_edit.setMinimumWidth(200)
        date_layout.addWidget(self.duration_edit)
        form_column.addLayout(date_layout)
        
        # Chart Column
        chart_column = QVBoxLayout()
        self.progress_chart = QChartView()
        self.progress_chart.setMinimumSize(400, 300)
        self.progress_chart.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_column.addWidget(self.progress_chart)
        
        # Add columns to content layout
        content_layout.addLayout(form_column, 40)  # 40% width
        content_layout.addLayout(chart_column, 60)  # 60% width
        
        # Submit Button
        submit_btn = QPushButton("Create Learning Plan")
        submit_btn.setFixedHeight(45)
        submit_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 16px;
                min-width: 250px;
            }
            QPushButton:hover { background-color: #219a52; }
            QPushButton:disabled { background-color: #95a5a6; }
        """)
        
        # Assemble main layout
        main_layout.addLayout(content_layout)
        main_layout.addWidget(submit_btn, 0, Qt.AlignmentFlag.AlignCenter)
        main_layout.addStretch(1)
        
        self.setLayout(main_layout)
        
        # Connections
        self.name_edit.textChanged.connect(self.validate_name)
        self.pages_spin.valueChanged.connect(self.update_visualization)
        self.daily_spin.valueChanged.connect(self.update_visualization)
        self.duration_edit.dateChanged.connect(self.update_visualization)
        submit_btn.clicked.connect(self.create_lesson)
        
        self.update_visualization()


    def validate_name(self):
        name = self.name_edit.text().strip()
        exists = name in self.config.data['lessons']
        self.name_validator.setPixmap(QIcon.fromTheme(
            "dialog-error" if exists else "dialog-ok-apply"
        ).pixmap(20, 20))

    def update_visualization(self):
        chart = QChart()
        series = QPieSeries()
        
        total = self.pages_spin.value()
        daily = self.daily_spin.value()
        days_needed = total / daily
        days_available = QDate.currentDate().daysTo(self.duration_edit.date())
        
        if days_available > 0:
            progress = min(1, days_needed / days_available)
            series.append("Required Days", days_needed)
            series.append("Available Days", max(0, days_available - days_needed))
            
            slice = series.slices()[0]
            slice.setColor(QColor("#e74c3c" if days_needed > days_available else "#2ecc71"))
            slice.setLabelVisible(True)
            
            if days_needed <= days_available:
                slice = series.slices()[1]
                slice.setColor(QColor("#27ae60"))
        else:
            series.append("Invalid Date", 1).setColor(QColor("#e74c3c"))
        
        chart.addSeries(series)
        chart.setTitle("Time Distribution")
        chart.legend().setVisible(False)
        self.progress_chart.setChart(chart)

    def create_lesson(self):
        name = self.name_edit.text().strip()
        pages = self.pages_spin.value()
        daily = self.daily_spin.value()
        
        if not name:
            self.show_error("Name cannot be empty!")
            return
            
        if name in self.config.data['lessons']:
            self.show_error("Lesson already exists!")
            return
            
        try:
            self.config.add_lesson(name, pages, daily)
            self.show_success()
            self.reset_form()
        except Exception as e:
            self.show_error(str(e))

    def show_error(self, message):
        QMessageBox.critical(self, "Error", message)
        
    def show_success(self):
        QMessageBox.information(self, "Success", 
            "Lesson plan created successfully!\n\n"
            f"• Total pages: {self.pages_spin.value()}\n"
            f"• Daily target: {self.daily_spin.value()} pages\n"
            f"• Estimated completion: {self.duration_edit.date().toString('MMMM yyyy')}"
        )

    def reset_form(self):
        self.name_edit.clear()
        self.pages_spin.setValue(100)
        self.daily_spin.setValue(10)
        self.duration_edit.setDate(QDate.currentDate().addMonths(1))

class StatsGraph(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        self.update_graph()

    def update_graph(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        dates = []
        pages = []
        time_spent = []
        
        for entry in self.config.data['stats']['progress']:
            if not entry['Skipped']:
                dates.append(datetime.strptime(entry['Date'], "%Y-%m-%d"))
                pages.append(entry['NumberOfPages'])
                time_spent.append(entry['TimeFinished'] / 3600)  # Convert to hours
                
        ax.plot(dates, pages, label='Pages Studied')
        ax.plot(dates, time_spent, label='Hours Spent')
        ax.legend()
        ax.set_xlabel('Date')
        ax.set_title('Study Progress')
        self.canvas.draw()


class RewardShop(QWidget):
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config = config_manager
        self.reward_history = self.config.data.setdefault('rewards', {}).setdefault('history', [])
        self.active_cooldowns = self.config.data['rewards'].setdefault('cooldowns', {})
        
        # Define rewards first
        self.reward_categories = {
            "Breaks": [
                {
                    "name": "5-Minute Break",
                    "cost": 100,
                    "icon": "⏳",
                    "color": "#3498db",
                    "action": self.add_break,
                    "cooldown": 60*4,  # 4 hours in minutes
                    "max_uses": 3,
                    "remaining_uses": self.config.data['rewards'].setdefault('5_minute_break_remaining', 3)
                },
                {
                    "name": "15-Minute Break",
                    "cost": 250,
                    "icon": "☕",
                    "color": "#2980b9",
                    "action": self.add_break,
                    "cooldown": 60*24,
                    "max_uses": 1,
                    "remaining_uses": self.config.data['rewards'].setdefault('15min_breaks', 1)
                }
            ],
            "Privileges": [
                {
                    "name": "Extra Day Off",
                    "cost": 1000,
                    "icon": "🌴", 
                    "color": "#2ecc71",
                    "action": self.add_extra_day,
                    "cooldown": 60*24*7,
                    "max_uses": 1,
                    "remaining_uses": self.config.data['rewards'].setdefault('extra_days', 1)
                },
                {
                    "name": "Custom Theme",
                    "cost": 500,
                    "icon": "🎨",
                    "color": "#9b59b6",
                    "action": self.apply_theme,
                    "cooldown": 0,
                    "max_uses": 0,
                    "remaining_uses": -1  # Unlimited
                }
            ]
        }

        # Now setup UI
        self.setup_ui()
        self.setStyleSheet("""
            QWidget { 
                background-color: #2c3e50;
                font-family: 'Segoe UI';
                color: #ecf0f1;
            }
            QLabel { 
                font-size: 16px;
            }
            QPushButton { 
                border-radius: 15px;
                padding: 20px;
                font-size: 16px;
                min-width: 250px;
                border: 2px solid #34495e;
            }
            QPushButton:disabled {
                background-color: #7f8c8d;
                color: #2c3e50;
            }
            QTabWidget::pane {
                border: 0;
            }
            QTabBar::tab {
                background: #34495e;
                color: #bdc3c7;
                padding: 10px;
                min-width: 100px;
            }
            QTabBar::tab:selected {
                background: #2ecc71;
                color: #2c3e50;
            }
        """)

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)
        
        # Points display
        self.points_label = QLabel()
        self.points_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.points_label)
        
        # Category tabs
        self.tab_widget = QTabWidget()
        for category, rewards in self.reward_categories.items():
            tab = QWidget()
            tab_layout = QGridLayout()
            tab_layout.setSpacing(20)
            tab_layout.setContentsMargins(20, 20, 20, 20)
            
            for i, reward in enumerate(rewards):
                btn = self.create_reward_button(reward)
                tab_layout.addWidget(btn, i//2, i%2)
            
            tab.setLayout(tab_layout)
            self.tab_widget.addTab(tab, category)
        
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)
        
        # Connect config changes
        self.config.dataChanged.connect(self.update_ui)
        self.update_ui()

    def create_reward_button(self, reward):
        btn = QPushButton()
        self.update_button_appearance(btn, reward)
        
        # Store reward data in button properties
        btn.setProperty("reward_data", reward)
        btn.clicked.connect(lambda: self.handle_purchase(btn))
        return btn

    def update_button_appearance(self, button, reward):
        # Add cooldown indicator to button text
        cooldown_status = ""
        if self.is_on_cooldown(reward):
            last_used = datetime.fromisoformat(self.active_cooldowns[reward['name']])
            remaining = reward['cooldown'] - (datetime.now() - last_used).total_seconds()//60
            cooldown_status = f"\n🕒 {remaining}min cooldown"

        uses_text = "∞" if reward['max_uses'] == 0 else \
                  str(reward['remaining_uses']) if reward['remaining_uses'] > 0 else "🔒"
        
        button.setText(
            f"{reward['icon']} {reward['name']}\n"
            f"💰 {reward['cost']} points\n"
            f"🔄 {uses_text}{cooldown_status}"
        )

        # Dynamic styling based on availability
        base_style = f"""
            QPushButton {{
                background-color: {reward['color']};
                color: #2c3e50;
                border: 2px solid {QColor(reward['color']).darker(150).name()};
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {QColor(reward['color']).lighter(120).name()};
            }}
        """
        
        if self.is_on_cooldown(reward) or reward['remaining_uses'] <= 0:
            base_style += """
                QPushButton {
                    background-color: #7f8c8d;
                    color: #2c3e50;
                    border: 2px solid #95a5a6;
                }
            """
        
        button.setStyleSheet(base_style)
        button.setToolTip(self.get_reward_tooltip(reward))
    def get_reward_tooltip(self, reward):
        tooltip = f"<b>{reward['name']}</b><br>"
        tooltip += f"📝 {reward['description']}<br>" if 'description' in reward else ""
        tooltip += f"⏳ Cooldown: {reward['cooldown']//60}h<br>" if reward['cooldown'] > 0 else ""
        tooltip += f"🎯 Uses remaining: {reward['remaining_uses'] if reward['max_uses'] > 0 else 'Unlimited'}"
        return tooltip

    def handle_purchase(self, button):
        reward = button.property("reward_data")
        
        # Check conditions
        if not self.validate_purchase(reward):
            return
            
        # Deduct points
        self.config.data['stats']['points'] -= reward['cost']
        
        # Execute reward action
        try:
            reward['action'](reward)
            self.record_purchase(reward)
            self.update_ui()
            self.config.save_config()
            
            # Animate purchase
            self.animate_purchase(button)
            self.show_success_message(reward)
            
        except Exception as e:
            self.show_error_message(f"Failed to apply reward: {str(e)}")
            # Rollback points
            self.config.data['stats']['points'] += reward['cost']

    def validate_purchase(self, reward):
        # Check points
        if self.config.data['stats']['points'] < reward['cost']:
            self.show_error_message("Insufficient points!")
            return False
            
        # Check uses
        if reward['max_uses'] > 0 and reward['remaining_uses'] <= 0:
            self.show_error_message("No uses remaining for this reward!")
            return False
            
        # Check cooldown
        last_used = self.active_cooldowns.get(reward['name'])
        if last_used and (datetime.now() - datetime.fromisoformat(last_used)).total_seconds()/60 < reward['cooldown']:
            remaining = int(reward['cooldown'] - (datetime.now() - datetime.fromisoformat(last_used)).total_seconds()/60)
            self.show_error_message(f"Available in {remaining} minutes")
            return False
            
        return True

    def record_purchase(self, reward):
        # Update remaining uses
        if reward['max_uses'] > 0:
            reward['remaining_uses'] -= 1
            self.config.data['rewards'][f"{reward['name'].lower().replace(' ', '_')}_remaining"] = reward['remaining_uses']
        
        # Record cooldown
        self.active_cooldowns[reward['name']] = datetime.now().isoformat()
        self.config.data['rewards']['cooldowns'] = self.active_cooldowns
        
        # Add to history
        self.reward_history.append({
            "name": reward['name'],
            "timestamp": datetime.now().isoformat(),
            "cost": reward['cost']
        })

    def update_ui(self):
        # Update points display
        points = self.config.data['stats']['points']
        self.points_label.setText(
            f"<h1 style='margin: 0; color: #e74c3c;'>🪙 Points: {points}</h1>"
            f"<p style='color: #bdc3c7;'>Recent purchases: {len(self.reward_history)}</p>"
        )
        
        # Update all buttons
        for tab_index in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(tab_index)
            for button in tab.findChildren(QPushButton):
                reward = button.property("reward_data")
                self.update_button_appearance(button, reward)
                button.setDisabled(
                    self.config.data['stats']['points'] < reward['cost'] or
                    (reward['max_uses'] > 0 and reward['remaining_uses'] <= 0) or
                    self.is_on_cooldown(reward)
                )

    def is_on_cooldown(self, reward):
        last_used = self.active_cooldowns.get(reward['name'])
        if not last_used:
            return False
        elapsed = (datetime.now() - datetime.fromisoformat(last_used)).total_seconds()/60
        return elapsed < reward['cooldown']

    def animate_purchase(self, button):
        # Particle effect animation
        effect = QGraphicsOpacityEffect(button)
        button.setGraphicsEffect(effect)
        
        anim_group = QParallelAnimationGroup()
        
        # Fade animation
        fade_anim = QPropertyAnimation(effect, b"opacity")
        fade_anim.setDuration(800)
        fade_anim.setStartValue(1)
        fade_anim.setKeyValueAt(0.5, 0.2)
        fade_anim.setEndValue(1)
        
        # Scale animation
        scale_anim = QPropertyAnimation(button, b"geometry")
        scale_anim.setDuration(800)
        orig_geo = button.geometry()
        scale_anim.setKeyValueAt(0.5, QRect(
            orig_geo.x() - 15,
            orig_geo.y() - 15,
            orig_geo.width() + 30,
            orig_geo.height() + 30
        ))
        scale_anim.setEndValue(orig_geo)
        
        anim_group.addAnimation(fade_anim)
        anim_group.addAnimation(scale_anim)
        anim_group.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        anim_group.finished.connect(lambda: button.setGraphicsEffect(None))

    def add_break(self, reward):
        minutes = 5 if "5-Minute" in reward['name'] else 15
        next_study = next((
            s for s in self.config.data['stats']['progress']
            if not s['Skipped']
        ), None)
        
        if next_study:
            next_study['TimeFinished'] += minutes * 60
        else:
            raise ValueError("No upcoming study sessions found")

    def add_extra_day(self, reward):
        self.config.data['settings']['max_skipped_days'] += 1

    def apply_theme(self, reward):
        color = QColorDialog.getColor()
        if color.isValid():
            self.setStyleSheet(f"""
                QWidget {{ 
                    background-color: {color.darker(150).name()};
                    color: {color.lighter(150).name()};
                    font-family: 'Segoe UI';
                }}
                QPushButton {{
                    border: 2px solid {color.lighter(200).name()};
                }}
            """)
            self.config.data['settings']['theme'] = color.name()
            self.config.save_config()

    def show_error_message(self, message):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setText(message)
        msg.setWindowTitle("Error")
        msg.exec()

    def show_success_message(self, reward):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(f"🎉 Successfully purchased: {reward['name']}!")
        msg.setWindowTitle("Purchase Complete")
        msg.exec()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.block_window = None
        self.init_ui()
        self.init_schedule_checker()
        
    def init_ui(self):
        self.setWindowTitle("Infinity Learner")
        self.setMinimumSize(900, 700)
        
        # Create absolute path for icon
        icon_path = os.path.join(os.path.dirname(__file__), "study_icon.png")
        
        # Set application icon
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            print(f"Icon file not found at {icon_path}")
        
        tab_widget = QTabWidget()
        
        # Dashboard Tab
        dashboard_tab = QWidget()
        dash_layout = QVBoxLayout()
        
        stats = self.config.get_summary()
        stats_text = f"""
<h2>Study Statistics</h2>
<b>Points:</b> {stats['total_points']}<br>
<b>Consecutive Days:</b> {stats['consecutive_study_days']}<br>
<b>Total Time Spent:</b> {timedelta(seconds=stats['total_time_spent'])}<br>
<b>Skipped Days:</b> {stats['skipped_days']}
"""

        self.stats_label = QLabel(stats_text)
        dash_layout.addWidget(self.stats_label)
        
        self.calendar = InteractiveCalendar(self.config)
        dash_layout.addWidget(self.calendar)
        
        dashboard_tab.setLayout(dash_layout)
        
        # Create Program Tab
        # create_tab = CreateProgramTab(self.config)
        
        # # Progress Tab
        # progress_tab = StatsGraph(self.config)
        
        # # Reward Shop Tab
        # reward_tab = RewardShop(self.config)
        
        # Add Tabs
        tab_widget.addTab(dashboard_tab,QIcon(nice_path("icons/dashboard.png")), "Dashboard")
        tab_widget.addTab(EnhancedCreateProgramTab(self.config),QIcon(nice_path("icons/planning.png")), "Create Plan")
        tab_widget.addTab(ProgressTab(self.config),QIcon(nice_path("icons/analytics.png")), "Analysis")
        tab_widget.addTab(RewardShop(self.config),QIcon(nice_path("icons/cart.png")), "Reward Shop")
        tab_widget.addTab(LessonManager(self.config),QIcon(nice_path("icons/lesson.png")), "Manage Lessons")
        tab_widget.addTab(AssistantTab(self.config),QIcon(nice_path("icons/assistant.png")),"Assistant") # tab_widget.addTab(AssistantTab(self.config), QIcon(":assistant_icon.png"), "Assistant")
        self.setCentralWidget(tab_widget)
        
        # Menu Bar
        menu = self.menuBar()
        study_menu = menu.addMenu("Study")
        
        start_action = QAction("Start Study Session", self)
        start_action.triggered.connect(self.start_study)
        study_menu.addAction(start_action)
        
        # Schedule Monitor
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        self.tray_icon.show()
        theme_color = self.config.data['rewards']['theme_color']
        self.setStyleSheet(f"""
            QWidget {{ 
                background-color: {QColor(theme_color).name()};
                color: {QColor(theme_color).lighter(555).name()};
            }}
        """)
        
    def init_schedule_checker(self):
        self.schedule_timer = QTimer()
        self.schedule_timer.timeout.connect(self.check_schedule)
        self.schedule_timer.start(60000)  # Check every minute
        self.config_reload_timer = QTimer()
        self.config_reload_timer.timeout.connect(self.load_config)
        self.config_reload_timer.start(2000)
    def load_config(self):
        self.config.load_config()
        stats = self.config.get_summary()
        stats_text = f"""
<h2>Study Statistics</h2>
<b>Points:</b> {stats['total_points']}<br>
<b>Consecutive Days:</b> {stats['consecutive_study_days']}<br>
<b>Total Time Spent:</b> {timedelta(seconds=stats['total_time_spent'])}<br>
<b>Skipped Days:</b> {stats['skipped_days']}
"""
        self.stats_label.setText(stats_text)
    def check_schedule(self):
        if self.config.data['settings'].get('scheduled_time'):
            start = datetime.strptime(self.config.data['settings']['scheduled_time'], "%H:%M").time()
            end = (datetime.strptime(self.config.data['settings']['scheduled_time'], "%H:%M") + 
                timedelta(hours=2)).time()
            
            now = datetime.now().time()
            if start <= now <= end and not self.has_studied_today():
                self.config.block_user()
                
    def has_studied_today(self):
        today = datetime.now().strftime("%Y-%m-%d")
        return any(entry['Date'] == today and not entry['Skipped'] 
                   for entry in self.config.data['stats']['progress'])
                
    def start_study(self):
        lesson, ok = QInputDialog.getItem(
            self, "Select Lesson", "Choose a lesson:",
            self.config.data['lessons'].keys(), 0, False
        )
        
        if ok and lesson:
            self.config.start_study(lesson)
            self.show_block_window()
    def show_block_window(self):
        """Show blocking window within existing QApplication"""
        self.block_window = SecureBlockWindow(self.config)  # Changed from BlockWindow
        self.block_window.showFullScreen()
            
            
    def closeEvent(self, event):
        self.config.save_config()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Ensure font subsystem initialized
    font = app.font()
    if font.family() == "":
        app.setFont(QFont("Arial", 10))
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())