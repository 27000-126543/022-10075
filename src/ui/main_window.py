from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QStackedWidget, QLabel, QFrame, QStatusBar, QMessageBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon, QAction

from src.ui.import_window import ImportWindow
from src.ui.edit_window import EditWindow
from src.ui.export_window import ExportWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("混凝土浇筑旁站资料整理工具")
        self.init_ui()
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        header = self.create_header()
        main_layout.addWidget(header)
        
        nav_bar = self.create_navigation()
        main_layout.addWidget(nav_bar)
        
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("""
            QStackedWidget {
                background-color: #ffffff;
            }
        """)
        main_layout.addWidget(self.content_stack, 1)
        
        self.import_window = ImportWindow()
        self.edit_window = EditWindow()
        self.export_window = ExportWindow()
        
        self.content_stack.addWidget(self.import_window)
        self.content_stack.addWidget(self.edit_window)
        self.content_stack.addWidget(self.export_window)
        
        self.import_window.project_tree.itemClicked.connect(self.on_record_selected)
        self.export_window.jump_to_edit.connect(self.on_jump_to_edit)
        
        status_bar = QStatusBar()
        status_bar.showMessage("就绪 | 数据存储于: %USERPROFILE%/.concrete_log")
        self.setStatusBar(status_bar)
        
        self.current_record_id = None
    
    def create_header(self):
        header = QFrame()
        header.setFixedHeight(70)
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2c3e50, stop:1 #34495e);
                border: none;
            }
        """)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)
        
        icon_label = QLabel("🏗️")
        icon_label.setStyleSheet("font-size: 36px;")
        
        title_layout = QVBoxLayout()
        title_label = QLabel("混凝土浇筑旁站资料整理工具")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 20px;
                font-weight: bold;
            }
        """)
        
        subtitle_label = QLabel("监理旁站记录管理系统")
        subtitle_label.setStyleSheet("""
            QLabel {
                color: #bdc3c7;
                font-size: 12px;
            }
        """)
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        
        layout.addWidget(icon_label)
        layout.addLayout(title_layout)
        layout.addStretch()
        
        help_btn = QPushButton("❓ 帮助")
        help_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: 1px solid rgba(255,255,255,0.3);
                border-radius: 5px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.1);
            }
        """)
        help_btn.clicked.connect(self.show_help)
        layout.addWidget(help_btn)
        
        return header
    
    def create_navigation(self):
        nav = QFrame()
        nav.setFixedHeight(55)
        nav.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
            }
        """)
        
        layout = QHBoxLayout(nav)
        layout.setContentsMargins(20, 5, 20, 5)
        layout.setSpacing(10)
        
        self.nav_buttons = []
        
        nav_items = [
            ("📥 资料导入", 0, "导入照片、小票、委托单等资料"),
            ("✏️ 日志编排", 1, "编辑旁站记录内容，分配照片"),
            ("📄 打印导出", 2, "检查问题，导出PDF文件")
        ]
        
        for idx, (text, page_index, tooltip) in enumerate(nav_items):
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setMinimumHeight(45)
            btn.setMinimumWidth(150)
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self.get_nav_button_style(idx == 0))
            
            btn.clicked.connect(lambda checked, p=page_index, b=btn: self.switch_page(p, b))
            
            layout.addWidget(btn)
            self.nav_buttons.append(btn)
        
        layout.addStretch()
        
        self.page_hint = QLabel("选择项目和楼栋，开始导入资料")
        self.page_hint.setStyleSheet("color: #6c757d; font-size: 12px;")
        layout.addWidget(self.page_hint)
        
        if self.nav_buttons:
            self.nav_buttons[0].setChecked(True)
        
        return nav
    
    def get_nav_button_style(self, active):
        if active:
            return """
                QPushButton {
                    background-color: #4a90e2;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 8px 20px;
                }
                QPushButton:hover {
                    background-color: #357abd;
                }
                QPushButton:checked {
                    background-color: #2c5282;
                    border: 2px solid #1a365d;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #e9ecef;
                    color: #495057;
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                    padding: 8px 20px;
                }
                QPushButton:hover {
                    background-color: #dee2e6;
                }
                QPushButton:checked {
                    background-color: #4a90e2;
                    color: white;
                    font-weight: bold;
                }
            """
    
    def switch_page(self, page_index, button):
        for btn in self.nav_buttons:
            btn.setStyleSheet(self.get_nav_button_style(btn == button))
        
        self.content_stack.setCurrentIndex(page_index)
        
        hints = [
            "选择项目和楼栋，拖拽文件到右侧区域进行导入",
            "从左侧拖拽照片到对应段落旁边，编辑记录内容",
            "检查资料完整性问题，然后导出PDF文件"
        ]
        self.page_hint.setText(hints[page_index])
        
        if page_index == 1 and self.current_record_id:
            self.edit_window.on_record_selected(self.current_record_id)
        elif page_index == 2 and self.current_record_id:
            self.export_window.on_record_selected(self.current_record_id)
        
        if page_index == 2:
            self.export_window.refresh()
    
    def on_record_selected(self, item, column):
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        
        item_type, item_id = data
        if item_type == 'record':
            self.current_record_id = item_id
            
            if self.content_stack.currentIndex() == 1:
                self.edit_window.on_record_selected(item_id)
            elif self.content_stack.currentIndex() == 2:
                self.export_window.on_record_selected(item_id)
    
    def on_jump_to_edit(self, record_id, section_key):
        self.current_record_id = record_id
        
        self.switch_page(1, self.nav_buttons[1])
        
        self.edit_window.on_record_selected(record_id)
        
        if section_key:
            self.edit_window.focus_section(section_key)
    
    def show_help(self):
        help_text = """
        <h3>混凝土浇筑旁站资料整理工具</h3>
        <p><b>使用说明：</b></p>
        <ol>
            <li><b>资料导入</b>：新建项目和楼栋，创建浇筑记录，然后拖拽照片、罐车小票、试块委托单等文件进行导入</li>
            <li><b>日志编排</b>：选择浇筑记录，填写旁站记录内容，将照片拖拽到对应段落旁边</li>
            <li><b>打印导出</b>：系统自动检查资料完整性问题，然后生成可打印的PDF文件</li>
        </ol>
        <p><b>功能特点：</b></p>
        <ul>
            <li>📁 支持拖拽批量导入文件</li>
            <li>📋 提供旁站记录模板，快速填写</li>
            <li>🖼️ 照片拖拽关联到对应段落</li>
            <li>🔍 自动检查常见问题（签字、时间、方量等）</li>
            <li>📄 生成规范的PDF文档，便于盖章归档</li>
            <li>💾 数据本地存储，支持离线使用</li>
        </ul>
        <p><b>数据存储位置：</b> %USERPROFILE%/.concrete_log</p>
        """
        QMessageBox.information(self, "帮助说明", help_text)
    
    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            "确认退出",
            "确定要退出程序吗？\n所有数据已自动保存。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
