# Definitely not made using chatgpt (I swear) # Deepseek made it not chatgpt
import sys
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import psutil

try: # hopefully this works
    plt.style.use("seaborn-v0_8-darkgrid")
except:
        plt.style.use('seaborn-darkgrid')

class ProgressTab(QWidget): # I named it
    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        self.data = self.process_data()
        self.init_ui()
        self.config.dataChanged.connect(self.update_data)
        
    def init_ui(self):
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        control_panel = QHBoxLayout()
        
        self.metric_combo = QComboBox()
        self.metric_combo.addItems(["Pages Studied", "Time Spent", "Points Earned", "Productivity Score"])
        self.metric_combo.currentIndexChanged.connect(self.update_plots)
        
        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["Daily", "Weekly", "Monthly"])
        self.interval_combo.currentIndexChanged.connect(self.update_plots)
        
        self.annotation_check = QCheckBox("Show Annotations")
        self.annotation_check.setChecked(True)
        self.annotation_check.stateChanged.connect(self.update_plots)
        
        control_panel.addWidget(QLabel("Metric:"))
        control_panel.addWidget(self.metric_combo)
        control_panel.addWidget(QLabel("Interval:"))
        control_panel.addWidget(self.interval_combo)
        control_panel.addWidget(self.annotation_check)
        control_panel.addStretch()
        
        self.stats_label = QLabel()
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stats_label.setStyleSheet("font-size: 16px; padding: 10px;")
        # TRYNNA figure OUT? LOL
        self.figure = plt.figure(figsize=(10, 12), tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        main_layout.addLayout(control_panel)
        main_layout.addWidget(self.stats_label)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.canvas)
        
        self.create_plots()

    def process_data(self):
        # I know pandas I just forgot how to use it
        df = pd.DataFrame(columns=['Date', 'NumberOfPages', 'TimeFinished', 
                                  'PointsEarned', 'Skipped', 'Lesson'])
        
        try:
            config_data = self.config.data['stats']['progress']
            if config_data:
                df = pd.DataFrame(config_data)
        except KeyError as e:
            print(f"Config key error: {e}")
        
        if not df.empty and 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df[~df['Skipped']]
        else:
            df = pd.DataFrame(columns=['Date', 'NumberOfPages', 'TimeFinished',
                                      'PointsEarned', 'Skipped', 'Lesson'])
        
        
        if not df.empty:
            df['Productivity Score'] = (df['NumberOfPages'] * 0.4 + 
                                      (df['TimeFinished']/3600) * 0.6)
        else:
            df['Productivity Score'] = pd.NA
        
        try:
            start_date = df['Date'].min() if not df.empty else datetime.today()
            end_date = datetime.today()
            
            if pd.isna(start_date):
                start_date = end_date
                
            full_dates = pd.date_range(start=start_date, end=end_date, freq='D')
        except Exception as e:
            print(f"Date range error: {e}")
            full_dates = pd.date_range(end=datetime.today(), periods=1, freq='D')

        try:
            self.full_df = df.set_index('Date').reindex(full_dates).reset_index()
            self.full_df.rename(columns={'index': 'Date'}, inplace=True)
        except Exception as e:
            print(f"Dataframe creation error: {e}")
            self.full_df = pd.DataFrame({'Date': full_dates})

        return self.full_df

    def create_plots(self):
        self.figure.clear()
        
        gs = self.figure.add_gridspec(3, 2, height_ratios=[1.5, 1, 1])
        self.ax1 = self.figure.add_subplot(gs[0, :])  
        self.ax2 = self.figure.add_subplot(gs[1, 0])  
        self.ax3 = self.figure.add_subplot(gs[1, 1]) 
        self.ax4 = self.figure.add_subplot(gs[2, :]) 
        
        self.figure.subplots_adjust(hspace=0.5, wspace=0.3)
        
        self.update_plots()
        self.canvas.draw()

    def update_data(self):
        self.data = self.process_data()
        self.update_plots()
        self.update_stats_summary()

    def update_plots(self):
        metric = self.metric_combo.currentText()
        interval = self.interval_combo.currentText()
        show_annotations = self.annotation_check.isChecked()
        
        #Why I love python:
        for ax in [self.ax1, self.ax2, self.ax3, self.ax4]:
            ax.clear()
            
        try:
            self.plot_main_trend(metric, interval, show_annotations)
            
            self.plot_distribution(metric)
            
            self.plot_lessons_breakdown()
            
            self.plot_streaks()
            
            self.figure.tight_layout(pad=3.0)
            self.canvas.draw()
            self.update_stats_summary()
            
        except Exception as e:
            print(f"Error updating plots: {e}")

    def plot_main_trend(self, metric, interval, show_annotations):
        df = self.data.copy()
        
        if df.empty or 'Date' not in df.columns:
            self.ax1.text(0.5, 0.5, 'No study data available', 
                         ha='center', va='center', fontsize=12)
            return

        metric_map = {
            "Pages Studied": "NumberOfPages",
            "Time Spent": "TimeFinished",
            "Points Earned": "PointsEarned",
            "Productivity Score": "Productivity Score"
        }
        metric_col = metric_map[metric]
        
        try:
            if interval == "Daily":
                plot_df = df.groupby('Date')[metric_col].sum()
            elif interval == "Weekly":
                plot_df = df.resample('W-Mon', on='Date')[metric_col].sum()
            elif interval == "Monthly":
                plot_df = df.resample('M', on='Date')[metric_col].sum()
            
            if plot_df.empty:
                self.ax1.text(0.5, 0.5, 'No data for selected interval', 
                             ha='center', va='center', fontsize=12)
                return
            
            line = self.ax1.plot(plot_df.index, plot_df.values, 
                               marker='o', linestyle='-', color='#3498db')
            
            
            if show_annotations:
                
                for x, y in zip(plot_df.index, plot_df.values):
                    self.ax1.annotate(
                        f"{y:.0f}" if metric != "Productivity Score" else f"{y:.1f}",
                        (x, y),
                        textcoords="offset points",
                        xytext=(0,10),
                        ha='center',
                        fontsize=8
                    )
                    
            self.ax1.set_title(f"{metric} Trend ({interval})", fontsize=14)
            self.ax1.set_ylabel(metric)
            self.ax1.grid(True, alpha=0.3)
            self.ax1.tick_params(axis='x', rotation=45)
            
        except KeyError as e:
            print(f"Error in main trend plot: {e}")

    def plot_distribution(self, metric):
        metric_map = {
            "Pages Studied": "NumberOfPages",
            "Time Spent": "TimeFinished",
            "Points Earned": "PointsEarned",
            "Productivity Score": "Productivity Score"
        }
        metric_col = metric_map[metric]
        
        data = self.data[metric_col].dropna()
        if data.empty:
            self.ax2.text(0.5, 0.5, 'No data available', 
                         ha='center', va='center', fontsize=12)
            return
        
        self.ax2.hist(data, bins=15, color='#2ecc71', edgecolor='black')
        self.ax2.set_title(f"{metric} Distribution", fontsize=12)
        self.ax2.set_xlabel(metric)
        self.ax2.set_ylabel("Frequency")
        
        if (data <= 0).any():
            self.ax2.set_yscale('linear')
        else:
            self.ax2.set_yscale('linear')

    def plot_lessons_breakdown(self):
        lesson_data = self.data.groupby('Lesson')['NumberOfPages'].sum()
        lesson_data = lesson_data[lesson_data > 0]
        
        if not lesson_data.empty:
            colors = plt.cm.tab20(np.linspace(0, 1, len(lesson_data)))
            self.ax3.pie(lesson_data, 
                        labels=lesson_data.index,
                        autopct='%1.1f%%',
                        startangle=90,
                        colors=colors,
                        wedgeprops={'edgecolor': 'black'})
            self.ax3.set_title("Lesson Distribution", fontsize=12)

    def plot_streaks(self):
        streaks = []
        current_streak = 0
        
        for date in pd.date_range(start=self.data['Date'].min(), end=datetime.today()):
            if date.date() in self.data['Date'].dt.date.values:
                current_streak += 1
            else:
                if current_streak > 0:
                    streaks.append(current_streak)
                current_streak = 0
                
        if streaks:
            self.ax4.bar(range(len(streaks)), streaks, color='#9b59b6')
            self.ax4.set_title("Study Streaks History", fontsize=12)
            self.ax4.set_xlabel("Streak Number")
            self.ax4.set_ylabel("Days in Streak")
            
            max_streak = max(streaks)
            self.ax4.annotate(f"Longest Streak: {max_streak} days",
                             xy=(0.7, 0.9), xycoords='axes fraction',
                             fontsize=10, color='#34495e')

    def update_stats_summary(self):
        if self.data.empty:
            self.stats_label.setText("No study data available")
            return
            
        try:
            total_days = len(pd.date_range(
                start=self.data['Date'].min(), 
                end=datetime.today()
            ))
            
            studied_days = self.data['Date'].nunique()
            avg_productivity = self.data['Productivity Score'].mean()
            current_streak = self.calculate_current_streak()
            
            stats_text = (
                f"📅 Studied Days: {studied_days}/{total_days} | "
                f"🔥 Current Streak: {current_streak} | "
                f"⚡ Avg Productivity: {avg_productivity:.1f}"
            )
            self.stats_label.setText(stats_text)
        except Exception as e:
            print(f"Error updating stats: {e}")
            self.stats_label.setText("Error calculating statistics")

    def calculate_current_streak(self):
        dates = sorted(self.data['Date'].dt.date.unique(), reverse=True)
        current_streak = 0
        
        for i in range(len(dates)):
            if dates[i] == datetime.today().date() - timedelta(days=i):
                current_streak += 1
            else:
                break
                
        return current_streak

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.context_menu(event.pos())

    def context_menu(self, pos):
        menu = QMenu(self)
        export_png = menu.addAction("Export as PNG")
        export_svg = menu.addAction("Export as SVG")
        reset_view = menu.addAction("Reset View")
        
        action = menu.exec(self.mapToGlobal(pos))
        
        if action == export_png:
            self.export_plot('png')
        elif action == export_svg:
            self.export_plot('svg')
        elif action == reset_view:
            self.toolbar.home()

    def export_plot(self, fmt):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Plot", "", f"{fmt.upper()} Files (*.{fmt})")
        if path:
            self.figure.savefig(path, format=fmt, dpi=300)
            QMessageBox.information(self, "Export Successful", 
                                   f"Plot exported successfully to {path}")