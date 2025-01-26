# GENERATED BY AI (sucks)
import os
import google.generativeai as genai
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6 import sip
import dotenv

class ChatMessage(QWidget):
    actionRequested = pyqtSignal(str, object)  # action_type, message
    
    def __init__(self, text, is_user=True, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.text = text
        self.uuid = QUuid.createUuid().toString()
        self.init_ui()
        if not self.is_user:  # Add continue button only to AI responses
            self.add_continue_button()
        self.original_text = text  # Track original text
        self.edited_text = text
        self.is_editing = False
        self.action_bar = QWidget()
        self.setup_action_bar()
    def setup_action_bar(self):
        self.action_bar = QWidget(self)
        self.action_bar.setObjectName("actionBar")
        self.action_bar.setStyleSheet("""
            QWidget#actionBar {
                background: rgba(40, 41, 50, 0.9);
                border-radius: 8px;
                padding: 4px;
            }
        """)
        self.action_bar.hide()

        btn_layout = QHBoxLayout(self.action_bar)
        btn_layout.setContentsMargins(2, 2, 2, 2)
        btn_layout.setSpacing(4)

        # Delete Button
        self.delete_btn = QPushButton("🗑")
        self.delete_btn.setFixedSize(24, 24)
        self.delete_btn.clicked.connect(lambda: self.actionRequested.emit("delete", self))

        # Copy Button
        self.copy_btn = QPushButton("📋")
        self.copy_btn.setFixedSize(24, 24)
        self.copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.text))

        # Edit Button
        self.edit_btn = QPushButton("✏️")
        self.edit_btn.setFixedSize(24, 24)
        self.edit_btn.clicked.connect(lambda: self.actionRequested.emit("edit", self))

        # Regenerate Button (AI responses only)
        self.regenerate_btn = QPushButton("🔄")
        self.regenerate_btn.setFixedSize(24, 24)
        self.regenerate_btn.clicked.connect(lambda: self.actionRequested.emit("regenerate", self))
        self.regenerate_btn.setVisible(not self.is_user)

        # Continue Button (AI responses only)
        self.continue_btn = QPushButton("▶")
        self.continue_btn.setFixedSize(24, 24)
        self.continue_btn.clicked.connect(lambda: self.actionRequested.emit("continue", self))
        self.continue_btn.setVisible(not self.is_user)

        # Add buttons to layout
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.copy_btn)
        btn_layout.addWidget(self.edit_btn)
        if not self.is_user:
            btn_layout.addWidget(self.regenerate_btn)
            btn_layout.addWidget(self.continue_btn)
        
    def init_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Minimum)
        layout = QHBoxLayout()
        layout.setContentsMargins(20 if self.is_user else 50, 10, 50 if self.is_user else 20, 10)
        
        self.bubble = QLabel()
        self.bubble.setTextFormat(Qt.TextFormat.MarkdownText)
        self.bubble.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.bubble.setWordWrap(True)
        self.bubble.setText(self.text)
        self.bubble.setStyleSheet(f"""
            QLabel {{
                background-color: {'#655EF2' if self.is_user else '#2A2D3A'};
                color: white;
                border-radius: 12px;
                padding: 16px;
                margin: 4px 0;
                font-size: 14px;
            }}
        """)
        
        layout.addWidget(self.bubble, 1, Qt.AlignmentFlag.AlignRight if self.is_user else Qt.AlignmentFlag.AlignLeft)
        self.setLayout(layout)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        # Existing code...
        self.menu_btn = QToolButton(self.bubble)
        self.menu_btn.setObjectName("menuBtn")
        self.menu_btn.setText("⋮")
        self.menu_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                color: rgba(255,255,255,0.5);
                border: none;
                font-size: 18px;
                padding: 0 5px;
            }
            QToolButton:hover {
                color: white;
            }
        """)
        self.menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn.hide()
        
        # Position menu button
        self.menu_btn.move(self.bubble.width() - 30, 5)
        
        # Create context menu
        self.context_menu = QMenu()
        self.delete_action = self.context_menu.addAction("🗑 Delete")
        self.copy_action = self.context_menu.addAction("📋 Copy")
        
        if self.is_user:
            self.edit_action = self.context_menu.addAction("✏️ Edit")
            self.regenerate_action = self.context_menu.addAction("🔄 Regenerate")
        
        self.menu_btn.setMenu(self.context_menu)
        self.menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.add_menu_button()
    def add_continue_button(self):
        self.continue_btn = QToolButton(self.bubble)
        self.continue_btn.setText("...")
        self.continue_btn.setObjectName("continueBtn")
        self.continue_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                color: #655EF2;
                border: none;
                font-weight: bold;
                padding: 2px;
                margin-right: 5px;
            }
            QToolButton:hover {
                color: #7B73FF;
            }
        """)
        self.continue_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.continue_btn.hide()
        
        # Position in top-right corner
        self.continue_btn.move(self.bubble.width() - 60, 5)
        
        # Connect menu
        menu = QMenu()
        menu.addAction("↩ Continue Generation", lambda: self.actionRequested.emit("continue", self))
        self.continue_btn.setMenu(menu)
        self.continue_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    def add_menu_button(self):
        self.menu_btn = QToolButton(self.bubble)
        self.menu_btn.setObjectName("menuBtn")
        self.menu_btn.setText("⋮")
        self.menu_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                color: rgba(255,255,255,0.5);
                border: none;
                font-size: 18px;
                padding: 0 5px;
            }
            QToolButton:hover {
                color: white;
            }
        """)
        self.menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn.hide()
        
        # Create context menu
        self.context_menu = QMenu()
        self.delete_action = self.context_menu.addAction("🗑 Delete")
        self.delete_action.triggered.connect(lambda: self.actionRequested.emit("delete", self))
        
        self.copy_action = self.context_menu.addAction("📋 Copy")
        self.copy_action.triggered.connect(lambda: QApplication.clipboard().setText(self.text))
        
        
        self.edit_action = self.context_menu.addAction("✏️ Edit")
        self.edit_action.triggered.connect(lambda: self.actionRequested.emit("edit", self))
        if not self.is_user:
            self.regenerate_action = self.context_menu.addAction("🔄 Regenerate")
            self.regenerate_action.triggered.connect(
                lambda: self.actionRequested.emit("regenerate", self))

        self.menu_btn.setMenu(self.context_menu)
        self.menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    def resizeEvent(self, event):
        if not self.is_user:
            self.continue_btn.move(self.bubble.width() - 60, 5)
        self.menu_btn.move(self.bubble.width() - 30, 5)
        super().resizeEvent(event)
    def enterEvent(self, event):
        self.action_bar.show()
        # Position action bar at bottom-right of message
        pos = self.bubble.geometry().bottomRight()
        self.action_bar.move(pos.x() - self.action_bar.width() - 10, 
                           pos.y() - self.action_bar.height() + 5)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.action_bar.hide()
        super().leaveEvent(event)
    def show_context_menu(self, pos):
        menu = QMenu(self)
        delete_action = menu.addAction(QIcon("icons/delete.svg"), "Delete")
        delete_action.triggered.connect(lambda: self.actionRequested.emit("delete", self))
        
        if self.is_user:
            edit_action = menu.addAction(QIcon("icons/edit.svg"), "Edit")
            edit_action.triggered.connect(lambda: self.actionRequested.emit("edit", self))
            
            regenerate_action = menu.addAction(QIcon("icons/refresh.svg"), "Regenerate")
            regenerate_action.triggered.connect(lambda: self.actionRequested.emit("regenerate", self))
        
        menu.exec(self.mapToGlobal(pos))
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        delete_action = menu.addAction("🗑 Delete")
        delete_action.triggered.connect(lambda: self.actionRequested.emit("delete", self))
        
        if self.is_user:
            edit_action = menu.addAction("✏️ Edit")
            edit_action.triggered.connect(lambda: self.actionRequested.emit("edit", self))
            
            regenerate_action = menu.addAction("🔄 Regenerate")
            regenerate_action.triggered.connect(
                lambda: self.actionRequested.emit("regenerate", self))
        
        menu.addAction("📋 Copy", lambda: QApplication.clipboard().setText(self.text))
        menu.exec(event.globalPos())
    def start_edit(self):
        self.is_editing = True
        self.bubble.hide()
        
        self.editor = QTextEdit(self)
        self.editor.setPlainText(self.bubble.text())
        self.editor.setStyleSheet("""
            QTextEdit {
                background: #3A3C46;
                border: 2px solid #655EF2;
                border-radius: 8px;
                padding: 12px;
                color: white;
                min-height: 100px;
            }
        """)
        
        # Edit action bar
        edit_actions = QWidget()
        btn_layout = QHBoxLayout(edit_actions)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_edit)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_edit)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        layout = QVBoxLayout(self)
        layout.addWidget(self.editor)
        layout.addWidget(edit_actions)
        
        self.adjustSize()
    def cancel_edit(self):
        self.bubble.setText(self.edited_text)
        self.end_edit()
    def save_edit(self):
        new_text = self.editor.toPlainText()
        self.bubble.setText(new_text)
        self.end_edit()
        self.actionRequested.emit("edit_saved", self)
    def end_edit(self):
        self.is_editing = False
        self.editor.deleteLater()
        self.button_container.deleteLater()
        self.bubble.show()
        self.adjustSize()
        self.parent().adjustSize()
        
class TypingIndicator(QWidget):
    def __init__(self):
        super().__init__()
        self.dots = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_dots)
        self.timer.start(500)
        self.setFixedSize(100, 30)
        
    def update_dots(self):
        self.dots = (self.dots + 1) % 4
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        
        for i in range(3):
            alpha = 255 if i < self.dots else 80
            painter.setBrush(QColor(101, 116, 242, alpha))
            painter.drawEllipse(20 + i*24, 10, 8, 8)

class AssistantWorker(QThread):
    responseReceived = pyqtSignal(str)
    errorOccurred = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, prompt, api_key):
        super().__init__()
        self.prompt = prompt
        self.api_key = api_key
        self.stop_requested = False
        self.setTerminationEnabled(True)
    def run(self):
        try:
            if self.stop_requested:
                return
                
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel('gemini-pro')
            chat = model.start_chat()
            response = chat.send_message(self.prompt, stream=True)
            
            full_response = ""
            for chunk in response:
                if self.stop_requested:
                    break
                try:
                    chunk_text = chunk.text
                    full_response += chunk_text
                    self.responseReceived.emit(chunk_text)
                
                except Exception as e:
                    self.errorOccurred.emit(f"Partial response error: {str(e)}")
            
            # Only emit finished if not stopped
            if not self.stop_requested:
                # Send final empty chunk to ensure completion
                self.responseReceived.emit("")
                QTimer.singleShot(0, self.finished.emit)
                
        except Exception as e:
            self.errorOccurred.emit(str(e))
        finally:
            if not self.stop_requested:
                QTimer.singleShot(0, self.finished.emit)

class ChatInput(QTextEdit):
    enterPressed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Ask me anything... (Ctrl+Enter for new line)")
        self.setStyleSheet("""
            QTextEdit {
                background: #2A2D3A;
                color: white;
                border: 2px solid #313442;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
            }
            QTextEdit:focus { border-color: #655EF2; }
        """)
        self.setMaximumHeight(120)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                # Insert new line
                super().keyPressEvent(event)
            else:
                # Emit enter pressed signal
                self.enterPressed.emit()
                event.accept()
        else:
            super().keyPressEvent(event)

class AssistantTab(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        self.history = []
        self.worker = None
        self.current_response = None
        self.typing_indicator = None  # Initialize as None
        self.init_ui()
        self.init_connections()
        

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Chat History
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.addStretch()
        self.chat_scroll.setWidget(self.chat_container)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, 
            QSizePolicy.Policy.MinimumExpanding)
        # Input Area
        input_frame = QFrame()
        input_frame.setStyleSheet("background: #242731; border-top: 1px solid #313442;")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(20, 15, 20, 15)

        self.input_field = ChatInput()
        self.input_field.setPlaceholderText("Ask me anything... (Ctrl+Enter for new line)")
        self.input_field.setStyleSheet("""
            QTextEdit {
                background: #2A2D3A;
                color: white;
                border: 2px solid #313442;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
            }
            QTextEdit:focus { border-color: #655EF2; }
        """)
        self.input_field.setMaximumHeight(120)

        self.send_btn = QPushButton(QIcon("icons/send.svg"), "")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: #655EF2;
                border-radius: 8px;
                padding: 12px;
                min-width: 40px;
            }
            QPushButton:hover { background: #7B73FF; }
            QPushButton:disabled { background: #3A3C46; }
        """)

        input_layout.addWidget(self.input_field, 1)
        input_layout.addWidget(self.send_btn)

        main_layout.addWidget(self.chat_scroll, 1)
        main_layout.addWidget(input_frame)
        self.setLayout(main_layout)
        self.setStyleSheet("""
    QPushButton {
        background: transparent;
        border: none;
        color: #A0A4B8;
        min-width: 24px;
        max-width: 24px;
    }
    QPushButton:hover {
        color: #FFFFFF;
        background: rgba(255,255,255,0.1);
        border-radius: 4px;
    }
    QScrollArea {
        border: none;
        background: #1A1B26;
    }
""")
    def init_connections(self):
        self.send_btn.clicked.connect(self.send_message)
        self.input_field.enterPressed.connect(self.send_message)

    def handle_key_press(self, event):
        if event.key() == Qt.Key.Key_Return and not event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.send_message()
        else:
            super(QTextEdit, self.input_field).keyPressEvent(event)

    def send_message(self):
        text = self.input_field.toPlainText().strip()
        if not text:
            return

        try:
            # Force enable send button
            self.send_btn.setEnabled(False)
            self.add_message(text, is_user=True)
            self.input_field.clear()
            self.process_message(text)
            
        except Exception as e:
            self.show_error(f"Message send failed: {str(e)}")
            self.send_btn.setEnabled(True)

    def process_message(self, text, is_continuation=False, is_regeneration=False):
        # Clean up any existing worker first
        if self.worker:
            self.worker.stop_requested = True
            self.worker.quit()
            self.worker.wait()
            self.worker.deleteLater()
            self.worker = None

        # Clear existing typing indicator
        if self.typing_indicator:
            self.typing_indicator.deleteLater()
            self.typing_indicator = None

        # API key check
        api_key = dotenv.get_key('./.env', "GEMINI_API_KEY")
        if not api_key:
            self.show_error("API key not configured!")
            return

        # Create new typing indicator
        self.typing_indicator = TypingIndicator()
        self.chat_layout.insertWidget(self.chat_layout.count()-1, self.typing_indicator)
        
        if not is_regeneration:
            self.current_response = ChatMessage("", False)
            self.current_response.actionRequested.connect(self.handle_message_action)
            self.chat_layout.insertWidget(self.chat_layout.count()-1, self.current_response)
        
        QApplication.processEvents()  # Force immediate UI update
       
        
        # Build context based on flags
        context = self.get_conversation_context() 
        if is_continuation:
            full_prompt = f"Continue this exactly:\n{context}\n{text}"
        elif is_regeneration:
            full_prompt = f"Regenerate this response:\n{context}\n{text}"
        else:
            full_prompt = text

        # Start worker thread
        self.worker = AssistantWorker(full_prompt, api_key)
        
        # Use lambda to capture worker reference
        self.worker.responseReceived.connect(lambda t: self.append_response(t))
        self.worker.errorOccurred.connect(lambda e: self.show_error(e))
        self.worker.finished.connect(lambda: self.finalize_response())
        
        # Add direct cleanup connection
        self.worker.finished.connect(self.worker.deleteLater)
        
        self.worker.start()
    def get_conversation_context(self):
        # Get last 3 messages for context
        context_messages = []
        for item in self.history[-3:]:
            role = "User" if item['type'] == 'user' else "Assistant"
            context_messages.append(f"{role}: {item['text']}")
        return "\n".join(context_messages)

    def append_response(self, text):
        if not self.current_response:
            self.current_response = ChatMessage("", False)
            self.current_response.actionRequested.connect(self.handle_message_action)
            self.chat_layout.insertWidget(self.chat_layout.count()-1, self.current_response)
        
        # Only update if we have text
        if text:
            current_text = self.current_response.bubble.text()
            self.current_response.bubble.setText(current_text + text)
            
            # Force immediate layout update
            self.current_response.bubble.updateGeometry()
            self.chat_container.updateGeometry()
            self.scroll_to_bottom()

    def finalize_response(self):
        try:
            # Clean up worker
            if self.worker:
                self.worker.stop_requested = True
                self.worker.quit()
                self.worker.wait()
                self.worker.deleteLater()
                self.worker = None

            # Clean up typing indicator
            if self.typing_indicator:
                self.typing_indicator.deleteLater()
                self.typing_indicator = None
                QApplication.processEvents()

            # Ensure final text formatting
            if self.current_response:
                text = self.current_response.bubble.text().strip()
                self.current_response.bubble.setText(text)
                self.history.append({
                    'type': 'assistant',
                    'text': text,
                    'widget': self.current_response
                })
                self.current_response = None

            self.send_btn.setEnabled(True)
            QApplication.processEvents()

        except Exception as e:
            print(f"Cleanup error: {str(e)}")
    def truncate_history_from(self, index):
        """Remove all messages from history starting at given index"""
        while len(self.history) > index:
            item = self.history.pop()
            widget = item['widget']
            self.chat_layout.removeWidget(widget)
            widget.deleteLater()
    def add_message(self, text, is_user=True):
        message = ChatMessage(text, is_user)
        message.actionRequested.connect(self.handle_message_action)
        self.chat_layout.insertWidget(self.chat_layout.count()-1, message)
        self.history.append({
            'type': 'user' if is_user else 'assistant',
            'text': text,
            'widget': message
        })
        self.scroll_to_bottom()

    def handle_message_action(self, action_type, message):
        if self.worker:
            self.worker.stop_requested = True
            self.worker.quit()
            self.worker.wait()
            self.worker = None
        
        # Clear typing indicator for any action
        if self.typing_indicator:
            self.typing_indicator.deleteLater()
            self.typing_indicator = None
        if action_type == "delete":
            self.delete_message(message)
        elif action_type == "edit":
            self.edit_message(message)
        elif action_type == "regenerate":
            self.regenerate_message(message)
        elif action_type == "continue":
            self.continue_generation(message)
        elif action_type == "edit":
            message.start_edit()
        elif action_type == "edit_saved":
            self.handle_edit_saved(message)
    def handle_edit_saved(self, message):
        # Update history record
        for item in self.history:
            if item['widget'] == message:
                item['text'] = message.edited_text
                break
                
        # If edited message is AI response, update subsequent messages
        if not message.is_user:
            self.regenerate_from(message)
    def regenerate_from(self, message):
        index = next((i for i, item in enumerate(self.history) if item['widget'] == message), -1)
        if index == -1:
            return
            
        # Truncate subsequent messages
        self.truncate_history_from(index + 1)
        
        # Regenerate with full context
        context = self.get_conversation_context()
        self.process_message(context + "\n" + message.edited_text, is_regeneration=True)
    def continue_generation(self, message):
        if self.worker:
            return
            
        # Get last 500 characters as context
        context = message.text[-500:]
        
        # Create new continuation message
        self.current_response = ChatMessage("", False)
        self.chat_layout.insertWidget(self.chat_layout.count()-1, self.current_response)
        
        # Build continuation prompt
        prompt = f"Continue this exactly from where it left off:\n{context}"
        self.process_message(prompt, is_continuation=True)
    def delete_message(self, message):
        # Stop any ongoing generation for this message
        if message == self.current_response and self.worker:
            self.worker.stop_requested = True
            self.worker.quit()
            self.worker.wait()
            self.worker = None
            
        # Remove from both sides (user and assistant)
        for i in reversed(range(self.chat_layout.count())):
            widget = self.chat_layout.itemAt(i).widget()
            if widget == message:
                self.chat_layout.removeWidget(widget)
                widget.deleteLater()
                break
                
        # Update history
        self.history = [item for item in self.history if item['widget'] != message]

    def edit_message(self, message):
        if not message.is_user:
            return
            
        # Create editor dialog
        editor_dialog = QDialog(self)
        editor_dialog.setWindowTitle("Edit Message")
        editor_dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(editor_dialog)
        
        # Create editor with original text
        editor = QTextEdit(message.text)
        editor.setStyleSheet("""
            QTextEdit {
                background: #3A3C46;
                border: 2px solid #655EF2;
                border-radius: 8px;
                padding: 12px;
                color: white;
                min-height: 150px;
            }
        """)
        
        # Create button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        
        # Connect signals using partial to maintain references
        button_box.accepted.connect(lambda: self.save_edit(message, editor))
        button_box.rejected.connect(editor_dialog.reject)
        
        layout.addWidget(editor)
        layout.addWidget(button_box)
        
        if editor_dialog.exec() == QDialog.DialogCode.Accepted:
            # Update message bubble text if saved
            message.bubble.setText(editor.toPlainText())
            
        # Explicit cleanup
        editor.deleteLater()
        editor_dialog.deleteLater()

    def save_edit(self, message, editor):
        # Check if editor still exists
        if not sip.isdeleted(editor):
            new_text = editor.toPlainText()
            message.bubble.setText(new_text)
            
            # Update history
            for item in self.history:
                if item['widget'] == message:
                    item['text'] = new_text
                    break

    def cancel_edit(self, message, editor):
        editor.deleteLater()
        self.chat_layout.itemAt(self.chat_layout.indexOf(editor)).widget().deleteLater()
        message.show()

    def regenerate_message(self, message):
        try:
            # Force cleanup first
            self.finalize_response()
            
            # Find message index
            index = next((i for i, item in enumerate(self.history) 
                        if item['widget'] == message), -1)
            
            if index == -1:
                return

            # Truncate history
            self.truncate_history_from(index)
            
            # Clear input field and set regeneration text
            self.input_field.setPlainText(message.edited_text or message.text)
            self.send_message()
            
        except Exception as e:
            self.show_error(f"Regeneration failed: {str(e)}")

    def show_error(self, text):
        try:
            error_msg = ChatMessage(f"⚠️ Error: {text}", False)
            error_msg.bubble.setStyleSheet("background: #E74C3C;")
            self.chat_layout.insertWidget(self.chat_layout.count()-1, error_msg)
            
            # Force immediate cleanup
            self.finalize_response()
            
            # Ensure input remains usable
            self.send_btn.setEnabled(True)
            QApplication.processEvents()
            
        except Exception as e:
            print(f"Error handling failed: {str(e)}")

    def scroll_to_bottom(self):
        # Use queued connection to ensure layout updates complete
        QTimer.singleShot(50, self._perform_scroll)

    def _perform_scroll(self):
        try:
            scroll_bar = self.chat_scroll.verticalScrollBar()
            if scroll_bar:
                scroll_bar.setValue(scroll_bar.maximum())
        except Exception as e:
            print(f"Scroll error: {str(e)}")
    
    def clear_history(self):
        for i in reversed(range(self.chat_layout.count())):
            widget = self.chat_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        self.history.clear()
