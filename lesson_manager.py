from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QProgressBar, QDialog, QFormLayout, QLineEdit,
    QSpinBox, QDialogButtonBox, QMessageBox, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon

class LessonManager(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        self.init_ui()
        self.config.dataChanged.connect(self.populate_lessons_table)

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        self.setLayout(main_layout)

        # Lesson Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Name", "Total Pages", "Daily Pages", "Completed", "Progress"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.cellClicked.connect(self.update_button_states)

        # Control Buttons
        control_layout = QVBoxLayout()
        buttons = [
            ("Add Lesson", "green", self.add_lesson),
            ("Edit Lesson", "blue", self.edit_lesson),
            ("Delete Lesson", "red", self.delete_lesson),
            ("Start/Stop Study", "orange", self.toggle_study_status),
        ]

        for text, color, handler in buttons:
            btn = QPushButton(text)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    padding: 10px;
                    border-radius: 5px;
                    font-weight: bold;
                }}
                QPushButton:disabled {{
                    background-color: gray;
                }}
            """)
            btn.clicked.connect(handler)
            control_layout.addWidget(btn)

        control_layout.addStretch()
        main_layout.addWidget(self.table, 75)
        main_layout.addLayout(control_layout, 25)

        self.populate_lessons_table()
        self.update_button_states()

    def populate_lessons_table(self):
        self.table.setRowCount(0)
        lessons = self.config.data['lessons']
        
        for row, (name, data) in enumerate(lessons.items()):
            self.table.insertRow(row)
            progress = (data['CompletedPages'] / data['NumberOfPages']) * 100 if data['NumberOfPages'] else 0

            # Create items for first 4 columns
            items = [
                QTableWidgetItem(name),
                QTableWidgetItem(str(data['NumberOfPages'])),
                QTableWidgetItem(str(data['StudyPagePerDay'])),
                QTableWidgetItem(str(data['CompletedPages'])),
            ]

            # Add items to the first 4 columns
            for col, item in enumerate(items):
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)

            # Add progress bar to 5th column
            progress_bar = QProgressBar()
            progress_bar.setValue(int(progress))
            progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid gray;
                    border-radius: 5px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #27ae60;
                }
            """)
            self.table.setCellWidget(row, 4, progress_bar)

            # Highlight active lessons (only first 4 columns have items)
            if data['IsStudying']:
                for col in range(4):  # Only iterate through columns 0-3
                    self.table.item(row, col).setBackground(QColor('#DFF0D8'))

    def update_button_states(self):
        has_selection = bool(self.table.selectedItems())
        for btn in self.findChildren(QPushButton):
            if btn.text() != "Add Lesson":
                btn.setEnabled(has_selection)

    def add_lesson(self):
        dialog = LessonDialog(self.config)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config.save_config()

    def edit_lesson(self):
        selected_row = self.table.currentRow()
        if selected_row == -1:
            return

        lesson_name = self.table.item(selected_row, 0).text()
        dialog = LessonDialog(self.config, lesson_name)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config.save_config()

    def delete_lesson(self):
        selected_row = self.table.currentRow()
        if selected_row == -1:
            return

        lesson_name = self.table.item(selected_row, 0).text()
        lesson_data = self.config.data['lessons'][lesson_name]

        # Check for existing progress
        has_progress = any(entry['Lesson'] == lesson_name 
                          for entry in self.config.data['stats']['progress'])

        confirm_msg = f"Delete lesson '{lesson_name}'?"
        if has_progress:
            confirm_msg += "\n\nThis lesson has associated progress entries!"

        reply = QMessageBox.question(
            self, "Confirm Delete", confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            del self.config.data['lessons'][lesson_name]
            self.config.save_config()

    def toggle_study_status(self):
        selected_row = self.table.currentRow()
        if selected_row == -1:
            return

        lesson_name = self.table.item(selected_row, 0).text()
        lesson = self.config.data['lessons'][lesson_name]
        current_status = lesson['IsStudying']

        if current_status:
            lesson['IsStudying'] = False
        else:
            # Ensure only one active lesson
            for name, data in self.config.data['lessons'].items():
                if data['IsStudying']:
                    QMessageBox.warning(
                        self, "Study Conflict",
                        f"Cannot start {lesson_name} - {name} is already active!"
                    )
                    return
            lesson['IsStudying'] = True

        self.config.save_config()

class LessonDialog(QDialog):
    def __init__(self, config, lesson_name=None):
        super().__init__()
        self.config = config
        self.lesson_name = lesson_name
        self.is_edit_mode = lesson_name is not None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Edit Lesson" if self.is_edit_mode else "Add Lesson")
        self.setWindowIcon(QIcon(":edit.png"))
        layout = QFormLayout(self)

        # Name Field
        self.name_edit = QLineEdit()
        layout.addRow("Lesson Name:", self.name_edit)

        # Numeric Fields
        self.total_pages = QSpinBox()
        self.total_pages.setRange(1, 1000)
        self.daily_pages = QSpinBox()
        self.daily_pages.setRange(1, 100)
        self.completed_pages = QSpinBox()
        self.completed_pages.setRange(0, 0)

        # Connect total pages to completed pages maximum
        self.total_pages.valueChanged.connect(
            lambda v: self.completed_pages.setMaximum(v)
        )

        layout.addRow("Total Pages:", self.total_pages)
        layout.addRow("Daily Pages:", self.daily_pages)
        layout.addRow("Completed Pages:", self.completed_pages)

        # Load existing data if editing
        if self.is_edit_mode:
            lesson_data = self.config.data['lessons'][self.lesson_name]
            self.name_edit.setText(self.lesson_name)
            self.total_pages.setValue(lesson_data['NumberOfPages'])
            self.daily_pages.setValue(lesson_data['StudyPagePerDay'])
            self.completed_pages.setValue(lesson_data['CompletedPages'])

        # Dialog Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate_and_save)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def validate_and_save(self):
        new_name = self.name_edit.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Error", "Lesson name cannot be empty!")
            return

        # Check for name conflicts
        if (not self.is_edit_mode or new_name != self.lesson_name) and new_name in self.config.data['lessons']:
            QMessageBox.warning(self, "Error", "Lesson name already exists!")
            return

        # Create/update lesson data
        lesson_data = {
            'NumberOfPages': self.total_pages.value(),
            'StudyPagePerDay': self.daily_pages.value(),
            'CompletedPages': self.completed_pages.value(),
            'IsStudying': False
        }

        if self.is_edit_mode:
            # Handle name change
            if new_name != self.lesson_name:
                self.config.data['lessons'][new_name] = self.config.data['lessons'].pop(self.lesson_name)
            # Preserve study status
            lesson_data['IsStudying'] = self.config.data['lessons'][new_name]['IsStudying']
            
        self.config.data['lessons'][new_name] = lesson_data
        self.accept()