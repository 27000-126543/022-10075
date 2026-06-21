import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QFrame, QSplitter,
    QTreeWidget, QTreeWidgetItem, QAbstractItemView, QProgressDialog,
    QFileDialog, QCheckBox, QTextEdit, QSizePolicy, QScrollArea, QMenu
)
from PySide6.QtCore import Qt, QSize, Signal, QUrl
from PySide6.QtGui import QIcon, QColor, QPixmap, QDesktopServices, QAction

from src.database import db_manager
from src.utils import export_utils


class IssueListItem(QWidget):
    fix_requested = Signal(dict)

    def __init__(self, issue_data, parent=None):
        super().__init__(parent)
        self.issue_data = issue_data
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        level = self.issue_data.get('level', 'info')
        level_styles = {
            'error': {'bg': '#fef2f2', 'border': '#ef4444', 'text': '#991b1b', 'icon': '❌'},
            'warning': {'bg': '#fffbeb', 'border': '#f59e0b', 'text': '#92400e', 'icon': '⚠️'},
            'info': {'bg': '#eff6ff', 'border': '#3b82f6', 'text': '#1e40af', 'icon': 'ℹ️'}
        }
        style = level_styles.get(level, level_styles['info'])

        icon_label = QLabel(style['icon'])
        icon_label.setStyleSheet(f"font-size: 18px;")
        icon_label.setFixedWidth(30)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        message_label = QLabel(self.issue_data.get('message', ''))
        message_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {style['text']};")
        message_label.setWordWrap(True)
        text_layout.addWidget(message_label)

        suggestion = self.issue_data.get('suggestion', '')
        if suggestion:
            suggestion_label = QLabel(f"💡 {suggestion}")
            suggestion_label.setStyleSheet(f"font-size: 11px; color: {style['text']};")
            suggestion_label.setWordWrap(True)
            text_layout.addWidget(suggestion_label)

        layout.addLayout(text_layout, 1)

        section = self.issue_data.get('section')
        if section:
            fix_btn = QPushButton("去修复")
            fix_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {style['border']};
                    color: white;
                    padding: 5px 12px;
                    border: none;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    opacity: 0.9;
                }}
            """)
            fix_btn.setCursor(Qt.PointingHandCursor)
            fix_btn.clicked.connect(self._on_fix_clicked)
            layout.addWidget(fix_btn)

        self.setStyleSheet(f"""
            IssueListItem {{
                background-color: {style['bg']};
                border: 1px solid {style['border']};
                border-radius: 8px;
            }}
            IssueListItem:hover {{
                background-color: white;
            }}
        """)

    def _on_fix_clicked(self):
        self.fix_requested.emit(self.issue_data)


class ExportWindow(QWidget):
    jump_to_edit = Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_record_id = None
        self.issues = []
        self.init_ui()
        self.load_records()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        left_panel = self.create_left_panel()
        right_panel = self.create_right_panel()

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([280, 900])

        main_layout.addWidget(splitter)

    def create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)

        title_label = QLabel("📋 浇筑记录列表")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1f2937;")
        layout.addWidget(title_label)

        filter_layout = QVBoxLayout()
        filter_layout.setSpacing(6)

        project_row = QHBoxLayout()
        project_row.addWidget(QLabel("项目:"))
        self.project_filter = QComboBox()
        self.project_filter.currentIndexChanged.connect(self.on_filter_changed)
        self.project_filter.setStyleSheet("QComboBox { padding: 5px; }")
        project_row.addWidget(self.project_filter, 1)
        filter_layout.addLayout(project_row)

        building_row = QHBoxLayout()
        building_row.addWidget(QLabel("楼栋:"))
        self.building_filter = QComboBox()
        self.building_filter.currentIndexChanged.connect(self.on_filter_changed)
        self.building_filter.setStyleSheet("QComboBox { padding: 5px; }")
        building_row.addWidget(self.building_filter, 1)
        filter_layout.addLayout(building_row)

        layout.addLayout(filter_layout)

        self.record_tree = QTreeWidget()
        self.record_tree.setHeaderLabels(["浇筑日期", "构件部位", "状态"])
        self.record_tree.setColumnWidth(0, 100)
        self.record_tree.setColumnWidth(1, 160)
        self.record_tree.setColumnWidth(2, 80)
        self.record_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.record_tree.itemClicked.connect(self.on_record_clicked)
        self.record_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                padding: 4px;
            }
            QTreeWidget::item {
                padding: 4px;
                border-radius: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #dbeafe;
                color: #1e40af;
            }
        """)
        layout.addWidget(self.record_tree, 1)

        select_all_btn = QPushButton("☑️ 全选当前筛选")
        select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6;
                color: #374151;
                padding: 6px 12px;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
            }
        """)
        select_all_btn.clicked.connect(self.select_all_visible)
        layout.addWidget(select_all_btn)

        return panel

    def create_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)

        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #fef3c7;
                border: 1px solid #f59e0b;
                border-radius: 10px;
                padding: 12px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setSpacing(6)

        title = QLabel("⚠️ 资料完整性检查 - 导出前整改清单")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #92400e;")
        header_layout.addWidget(title)

        desc = QLabel("系统自动检测以下问题，点击『去修复』可直接跳转到编辑位置补全资料。修复完成后点击『重新检查』。")
        desc.setStyleSheet("font-size: 12px; color: #78350f;")
        desc.setWordWrap(True)
        header_layout.addWidget(desc)

        layout.addWidget(header_frame)

        self.current_record_label = QLabel("请在左侧选择一条浇筑记录")
        self.current_record_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #374151; margin-top: 8px;")
        layout.addWidget(self.current_record_label)

        issues_container = QFrame()
        issues_container.setStyleSheet("""
            QFrame {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
            }
        """)
        issues_layout = QVBoxLayout(issues_container)
        issues_layout.setContentsMargins(8, 8, 8, 8)

        issues_header = QHBoxLayout()
        issues_title = QLabel("🔍 检查结果")
        issues_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #1f2937;")
        issues_header.addWidget(issues_title)
        issues_header.addStretch()

        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("font-size: 12px;")
        issues_header.addWidget(self.stats_label)

        refresh_btn = QPushButton("🔄 重新检查")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                padding: 5px 12px;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        refresh_btn.clicked.connect(self.check_current_record)
        issues_header.addWidget(refresh_btn)

        issues_layout.addLayout(issues_header)

        self.issues_scroll = QScrollArea()
        self.issues_scroll.setWidgetResizable(True)
        self.issues_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.issues_content = QWidget()
        self.issues_list_layout = QVBoxLayout(self.issues_content)
        self.issues_list_layout.setContentsMargins(0, 0, 0, 0)
        self.issues_list_layout.setSpacing(6)
        self.issues_list_layout.addStretch()

        self.issues_scroll.setWidget(self.issues_content)
        issues_layout.addWidget(self.issues_scroll, 1)

        layout.addWidget(issues_container, 1)

        export_frame = QFrame()
        export_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                padding: 12px;
            }
        """)
        export_layout = QVBoxLayout(export_frame)
        export_layout.setSpacing(8)

        export_title = QLabel("📄 导出设置")
        export_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #1f2937;")
        export_layout.addWidget(export_title)

        options_layout = QHBoxLayout()

        self.include_photos_check = QCheckBox("包含照片")
        self.include_photos_check.setChecked(True)
        self.include_photos_check.setStyleSheet("QCheckBox { font-size: 12px; }")
        options_layout.addWidget(self.include_photos_check)

        self.include_attachments_check = QCheckBox("包含附件清单")
        self.include_attachments_check.setChecked(True)
        self.include_attachments_check.setStyleSheet("QCheckBox { font-size: 12px; }")
        options_layout.addWidget(self.include_attachments_check)

        options_layout.addStretch()
        export_layout.addLayout(options_layout)

        btn_layout = QHBoxLayout()

        preview_pdf_btn = QPushButton("👁️ 预览PDF")
        preview_pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: white;
                padding: 10px 18px;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4f46e5;
            }
        """)
        preview_pdf_btn.clicked.connect(self.preview_pdf)

        export_pdf_btn = QPushButton("📄 导出PDF")
        export_pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #16a34a;
                color: white;
                padding: 10px 22px;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #15803d;
            }
        """)
        export_pdf_btn.clicked.connect(self.export_pdf)

        batch_export_btn = QPushButton("📦 批量导出选中")
        batch_export_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: white;
                padding: 10px 18px;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7c3aed;
            }
        """)
        batch_export_btn.clicked.connect(self.batch_export)

        btn_layout.addStretch()
        btn_layout.addWidget(preview_pdf_btn)
        btn_layout.addWidget(export_pdf_btn)
        btn_layout.addWidget(batch_export_btn)
        export_layout.addLayout(btn_layout)

        layout.addWidget(export_frame)

        summary_frame = QFrame()
        summary_frame.setStyleSheet("""
            QFrame {
                background-color: #eff6ff;
                border: 1px solid #bfdbfe;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        summary_layout = QHBoxLayout(summary_frame)
        self.summary_label = QLabel("请选择一条记录进行检查和导出")
        self.summary_label.setStyleSheet("color: #1e40af; font-size: 12px; font-weight: bold;")
        self.summary_label.setAlignment(Qt.AlignCenter)
        summary_layout.addWidget(self.summary_label)

        layout.addWidget(summary_frame)

        return panel

    def load_records(self):
        self.project_filter.clear()
        self.project_filter.addItem("全部项目", None)

        projects = db_manager.get_all_projects()
        for project in projects:
            self.project_filter.addItem(project['name'], project['id'])

        self.load_building_filter()
        self.load_record_tree()

    def load_building_filter(self):
        self.building_filter.clear()
        self.building_filter.addItem("全部楼栋", None)

        project_id = self.project_filter.currentData()
        if project_id:
            buildings = db_manager.get_buildings_by_project(project_id)
            for building in buildings:
                self.building_filter.addItem(building['name'], building['id'])

    def load_record_tree(self):
        self.record_tree.clear()

        project_id = self.project_filter.currentData()
        building_id = self.building_filter.currentData()

        projects = db_manager.get_all_projects()
        for project in projects:
            if project_id and project['id'] != project_id:
                continue

            project_item = QTreeWidgetItem(self.record_tree, [project['name'], '', ''])
            project_item.setData(0, Qt.UserRole, ('project', project['id']))
            project_item.setExpanded(True)
            project_item.setForeground(0, QColor('#1e40af'))

            buildings = db_manager.get_buildings_by_project(project['id'])
            for building in buildings:
                if building_id and building['id'] != building_id:
                    continue

                building_item = QTreeWidgetItem(project_item, ['', building['name'], ''])
                building_item.setData(0, Qt.UserRole, ('building', building['id']))
                building_item.setExpanded(True)

                records = db_manager.get_pouring_records(project['id'], building['id'])
                for record in records:
                    record_item = QTreeWidgetItem(building_item, [
                        record['pouring_date'],
                        record['component_location'][:18] + ('...' if len(record['component_location']) > 18 else ''),
                        ''
                    ])
                    record_item.setData(0, Qt.UserRole, ('record', record['id']))
                    record_item.setCheckState(0, Qt.Unchecked)
                    record_item.setToolTip(1, record['component_location'])

                    attachments = db_manager.get_attachments_by_record(record['id'])
                    sign_records = db_manager.get_sign_records_by_record(record['id'])
                    issues = export_utils.check_record_issues(record, attachments, sign_records)

                    error_count = sum(1 for i in issues if i.get('level') == 'error')
                    warning_count = sum(1 for i in issues if i.get('level') == 'warning')
                    info_count = sum(1 for i in issues if i.get('level') == 'info')

                    if error_count > 0:
                        record_item.setForeground(2, QColor('#dc2626'))
                        record_item.setText(2, f"❌ {error_count}")
                        record_item.setToolTip(2, f"{error_count}个错误，{warning_count}个警告")
                    elif warning_count > 0:
                        record_item.setForeground(2, QColor('#d97706'))
                        record_item.setText(2, f"⚠️ {warning_count}")
                        record_item.setToolTip(2, f"{warning_count}个警告，{info_count}个提示")
                    else:
                        record_item.setForeground(2, QColor('#059669'))
                        record_item.setText(2, "✅")
                        record_item.setToolTip(2, "资料完整")

    def on_filter_changed(self):
        if self.sender() == self.project_filter:
            self.load_building_filter()
        self.load_record_tree()

    def on_record_clicked(self, item, column):
        data = item.data(0, Qt.UserRole)
        if not data:
            return

        item_type, item_id = data
        if item_type == 'record':
            self.current_record_id = item_id
            self.current_record_label.setText(f"📋 当前检查：{item.text(0)} - {item.toolTip(1)}")
            self.check_current_record()

    def select_all_visible(self):
        root = self.record_tree.invisibleRootItem()
        for i in range(root.childCount()):
            project_item = root.child(i)
            for j in range(project_item.childCount()):
                building_item = project_item.child(j)
                for k in range(building_item.childCount()):
                    record_item = building_item.child(k)
                    record_item.setCheckState(0, Qt.Checked)

    def clear_issues_list(self):
        while self.issues_list_layout.count() > 1:
            child = self.issues_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def check_current_record(self):
        self.clear_issues_list()

        if not self.current_record_id:
            self.stats_label.setText("")
            self.summary_label.setText("请选择一条记录进行检查和导出")
            return

        record = db_manager.get_pouring_record_by_id(self.current_record_id)
        if not record:
            return

        attachments = db_manager.get_attachments_by_record(self.current_record_id)
        sign_records = db_manager.get_sign_records_by_record(self.current_record_id)

        self.issues = export_utils.check_record_issues(record, attachments, sign_records)

        error_count = sum(1 for i in self.issues if i.get('level') == 'error')
        warning_count = sum(1 for i in self.issues if i.get('level') == 'warning')
        info_count = sum(1 for i in self.issues if i.get('level') == 'info')

        if self.issues:
            for issue in self.issues:
                issue_widget = IssueListItem(issue)
                issue_widget.fix_requested.connect(self.on_fix_requested)
                self.issues_list_layout.insertWidget(self.issues_list_layout.count() - 1, issue_widget)

            stats_parts = []
            if error_count > 0:
                stats_parts.append(f'<span style="color:#dc2626">❌ {error_count}个错误</span>')
            if warning_count > 0:
                stats_parts.append(f'<span style="color:#d97706">⚠️ {warning_count}个警告</span>')
            if info_count > 0:
                stats_parts.append(f'<span style="color:#2563eb">ℹ️ {info_count}个提示</span>')
            self.stats_label.setText(" | ".join(stats_parts))
            self.stats_label.setTextFormat(Qt.RichText)
        else:
            ok_label = QLabel("✅ 所有检查项已通过！资料完整。")
            ok_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #059669; padding: 20px;")
            ok_label.setAlignment(Qt.AlignCenter)
            self.issues_list_layout.insertWidget(0, ok_label)
            self.stats_label.setText('<span style="color:#059669">✅ 资料完整</span>')
            self.stats_label.setTextFormat(Qt.RichText)

        image_count = sum(1 for a in attachments if a.get('file_type') == 'image')
        doc_count = sum(1 for a in attachments if a.get('file_type') == 'document')

        summary_parts = []
        if error_count > 0 or warning_count > 0:
            if error_count > 0:
                summary_parts.append(f'<span style="color:#dc2626; font-weight:bold;">{error_count}个错误</span>')
            if warning_count > 0:
                summary_parts.append(f'<span style="color:#d97706; font-weight:bold;">{warning_count}个警告</span>')
        else:
            summary_parts.append('<span style="color:#059669; font-weight:bold;">✅ 资料完整</span>')

        self.summary_label.setText(
            f"{' | '.join(summary_parts)} | "
            f"照片: {image_count}张 | "
            f"文档: {doc_count}个 | "
            f"附件总数: {len(attachments)}个"
        )
        self.summary_label.setTextFormat(Qt.RichText)

    def on_fix_requested(self, issue_data):
        section = issue_data.get('section')
        if not section:
            QMessageBox.information(self, "提示", "此问题无法自动跳转，请在『资料导入』或『日志编排』窗口手动处理。")
            return

        if not self.current_record_id:
            return

        self.jump_to_edit.emit(self.current_record_id, section)

    def get_record_full_data(self, record_id):
        record = db_manager.get_pouring_record_by_id(record_id)
        if not record:
            return None

        projects = db_manager.get_all_projects()
        project_name = next((p['name'] for p in projects if p['id'] == record['project_id']), '')

        buildings = db_manager.get_buildings_by_project(record['project_id'])
        building_name = next((b['name'] for b in buildings if b['id'] == record['building_id']), '')

        record['project_name'] = project_name
        record['building_name'] = building_name

        attachments = db_manager.get_attachments_by_record(record_id)
        sign_records = db_manager.get_sign_records_by_record(record_id)

        return record, attachments, sign_records

    def preview_pdf(self):
        if not self.current_record_id:
            QMessageBox.warning(self, "提示", "请先选择一条浇筑记录")
            return

        record, attachments, sign_records = self.get_record_full_data(self.current_record_id)
        if not record:
            return

        temp_dir = os.path.join(os.path.expanduser("~"), ".concrete_log", "temp")
        os.makedirs(temp_dir, exist_ok=True)

        projects = db_manager.get_all_projects()
        buildings = db_manager.get_buildings_by_project(record['project_id'])
        default_name = export_utils.generate_filename(record, projects, buildings)

        temp_file = os.path.join(temp_dir, "preview_" + datetime.now().strftime("%Y%m%d%H%M%S") + "_" + default_name)

        try:
            progress = QProgressDialog("正在生成PDF...", "取消", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.show()

            progress.setValue(30)

            export_utils.generate_pdf(record, attachments, sign_records, temp_file)

            progress.setValue(100)

            if os.path.exists(temp_file):
                QDesktopServices.openUrl(QUrl.fromLocalFile(temp_file))
            else:
                QMessageBox.warning(self, "错误", "PDF生成失败")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成PDF时出错：{str(e)}")

    def export_pdf(self):
        if not self.current_record_id:
            QMessageBox.warning(self, "提示", "请先选择一条浇筑记录")
            return

        record, attachments, sign_records = self.get_record_full_data(self.current_record_id)
        if not record:
            return

        projects = db_manager.get_all_projects()
        buildings = db_manager.get_buildings_by_project(record['project_id'])
        default_name = export_utils.generate_filename(record, projects, buildings)

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出PDF",
            os.path.join(os.path.expanduser("~"), "Documents", default_name),
            "PDF文件 (*.pdf)"
        )

        if not file_path:
            return

        try:
            progress = QProgressDialog("正在导出PDF...", "取消", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.show()

            progress.setValue(30)

            export_utils.generate_pdf(record, attachments, sign_records, file_path)

            progress.setValue(100)

            if os.path.exists(file_path):
                QMessageBox.information(self, "成功", f"PDF已成功导出到：\n{file_path}")
            else:
                QMessageBox.warning(self, "错误", "PDF导出失败")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出PDF时出错：{str(e)}")

    def batch_export(self):
        selected_records = []

        root = self.record_tree.invisibleRootItem()
        for i in range(root.childCount()):
            project_item = root.child(i)
            for j in range(project_item.childCount()):
                building_item = project_item.child(j)
                for k in range(building_item.childCount()):
                    record_item = building_item.child(k)
                    if record_item.checkState(0) == Qt.Checked:
                        data = record_item.data(0, Qt.UserRole)
                        if data:
                            _, record_id = data
                            selected_records.append(record_id)

        if not selected_records:
            QMessageBox.warning(self, "提示", "请先勾选要导出的记录")
            return

        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择批量导出目录",
            os.path.join(os.path.expanduser("~"), "Documents")
        )

        if not dir_path:
            return

        success_count = 0
        fail_count = 0

        progress = QProgressDialog("正在批量导出...", "取消", 0, len(selected_records), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)

        projects = db_manager.get_all_projects()

        for idx, record_id in enumerate(selected_records):
            if progress.wasCanceled():
                break

            progress.setValue(idx)
            progress.setLabelText(f"正在导出第 {idx + 1}/{len(selected_records)} 个记录...")

            record, attachments, sign_records = self.get_record_full_data(record_id)
            if not record:
                fail_count += 1
                continue

            buildings = db_manager.get_buildings_by_project(record['project_id'])
            default_name = export_utils.generate_filename(record, projects, buildings)
            file_path = os.path.join(dir_path, default_name)

            try:
                export_utils.generate_pdf(record, attachments, sign_records, file_path)
                success_count += 1
            except Exception as e:
                fail_count += 1
                print(f"导出失败: {str(e)}")

        progress.setValue(len(selected_records))

        QMessageBox.information(
            self,
            "批量导出完成",
            f"成功导出: {success_count} 个\n失败: {fail_count} 个\n\n输出目录: {dir_path}"
        )

    def on_record_selected(self, record_id):
        if record_id:
            self.current_record_id = record_id

            root = self.record_tree.invisibleRootItem()
            for i in range(root.childCount()):
                project_item = root.child(i)
                for j in range(project_item.childCount()):
                    building_item = project_item.child(j)
                    for k in range(building_item.childCount()):
                        record_item = building_item.child(k)
                        data = record_item.data(0, Qt.UserRole)
                        if data and data[1] == record_id:
                            self.record_tree.setCurrentItem(record_item)
                            self.current_record_label.setText(f"📋 当前检查：{record_item.text(0)} - {record_item.toolTip(1)}")
                            break

            self.check_current_record()

    def refresh(self):
        self.load_records()
