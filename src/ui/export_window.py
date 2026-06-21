import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QFrame, QSplitter,
    QTreeWidget, QTreeWidgetItem, QAbstractItemView, QProgressDialog,
    QFileDialog, QCheckBox
)
from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtGui import QIcon, QColor, QDesktopServices

from src.database import db_manager
from src.utils import export_utils


class ExportWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_record_id = None
        self.issues = []
        self.init_ui()
        self.load_records()
    
    def init_ui(self):
        main_layout = QHBoxLayout(self)
        
        splitter = QSplitter(Qt.Horizontal)
        
        left_panel = self.create_left_panel()
        right_panel = self.create_right_panel()
        
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)
    
    def create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        title_label = QLabel("浇筑记录列表")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title_label)
        
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("项目:"))
        self.project_filter = QComboBox()
        self.project_filter.currentIndexChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.project_filter)
        
        filter_layout.addWidget(QLabel("楼栋:"))
        self.building_filter = QComboBox()
        self.building_filter.currentIndexChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.building_filter)
        
        layout.addLayout(filter_layout)
        
        self.record_tree = QTreeWidget()
        self.record_tree.setHeaderLabels(["日期", "部位", "状态"])
        self.record_tree.setColumnWidth(0, 120)
        self.record_tree.setColumnWidth(1, 200)
        self.record_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.record_tree.itemClicked.connect(self.on_record_clicked)
        layout.addWidget(self.record_tree, 1)
        
        select_all_btn = QPushButton("☑️ 全选当前筛选")
        select_all_btn.clicked.connect(self.select_all_visible)
        layout.addWidget(select_all_btn)
        
        return panel
    
    def create_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel)
        header_layout = QVBoxLayout(header_frame)
        
        title = QLabel("📋 资料完整性检查")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title)
        
        desc = QLabel("系统将自动检查常见问题，然后生成可打印的PDF文件")
        desc.setStyleSheet("color: #666;")
        header_layout.addWidget(desc)
        
        layout.addWidget(header_frame)
        
        check_frame = QFrame()
        check_frame.setFrameStyle(QFrame.StyledPanel)
        check_layout = QVBoxLayout(check_frame)
        
        check_title = QLabel("问题检查结果")
        check_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        check_layout.addWidget(check_title)
        
        self.issue_list = QListWidget()
        self.issue_list.setStyleSheet("""
            QListWidget {
                background-color: #fafafa;
                border-radius: 6px;
            }
        """)
        check_layout.addWidget(self.issue_list, 1)
        
        refresh_btn = QPushButton("🔍 重新检查")
        refresh_btn.clicked.connect(self.check_current_record)
        check_layout.addWidget(refresh_btn)
        
        layout.addWidget(check_frame)
        
        preview_frame = QFrame()
        preview_frame.setFrameStyle(QFrame.StyledPanel)
        preview_layout = QVBoxLayout(preview_frame)
        
        preview_title = QLabel("导出选项")
        preview_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        preview_layout.addWidget(preview_title)
        
        options_layout = QHBoxLayout()
        
        self.include_photos_check = QCheckBox("包含照片")
        self.include_photos_check.setChecked(True)
        options_layout.addWidget(self.include_photos_check)
        
        self.include_attachments_check = QCheckBox("包含附件清单")
        self.include_attachments_check.setChecked(True)
        options_layout.addWidget(self.include_attachments_check)
        
        self.include_sign_check = QCheckBox("包含签字栏")
        self.include_sign_check.setChecked(True)
        options_layout.addWidget(self.include_sign_check)
        
        options_layout.addStretch()
        preview_layout.addLayout(options_layout)
        
        btn_layout = QHBoxLayout()
        
        preview_pdf_btn = QPushButton("👁️ 预览PDF")
        preview_pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        preview_pdf_btn.clicked.connect(self.preview_pdf)
        
        export_pdf_btn = QPushButton("📄 导出PDF")
        export_pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        export_pdf_btn.clicked.connect(self.export_pdf)
        
        batch_export_btn = QPushButton("📦 批量导出选中")
        batch_export_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        batch_export_btn.clicked.connect(self.batch_export)
        
        btn_layout.addStretch()
        btn_layout.addWidget(preview_pdf_btn)
        btn_layout.addWidget(export_pdf_btn)
        btn_layout.addWidget(batch_export_btn)
        preview_layout.addLayout(btn_layout)
        
        layout.addWidget(preview_frame)
        
        summary_frame = QFrame()
        summary_frame.setFrameStyle(QFrame.StyledPanel)
        summary_layout = QHBoxLayout(summary_frame)
        
        self.summary_label = QLabel("请选择一条记录进行检查和导出")
        self.summary_label.setStyleSheet("color: #666; font-size: 12px;")
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
                        record['component_location'],
                        self.get_record_status(record)
                    ])
                    record_item.setData(0, Qt.UserRole, ('record', record['id']))
                    record_item.setCheckState(0, Qt.Unchecked)
                    
                    attachments = db_manager.get_attachments_by_record(record['id'])
                    sign_records = db_manager.get_sign_records_by_record(record['id'])
                    issues = export_utils.check_record_issues(record, attachments, sign_records)
                    
                    error_count = sum(1 for i in issues if i[0] == 'error')
                    warning_count = sum(1 for i in issues if i[0] == 'warning')
                    
                    if error_count > 0:
                        record_item.setForeground(2, QColor('#e74c3c'))
                        record_item.setText(2, f"❌ {error_count}错误 {warning_count}警告")
                    elif warning_count > 0:
                        record_item.setForeground(2, QColor('#f39c12'))
                        record_item.setText(2, f"⚠️ {warning_count}警告")
                    else:
                        record_item.setForeground(2, QColor('#27ae60'))
                        record_item.setText(2, "✅ 完整")
    
    def get_record_status(self, record):
        if record.get('supervisor_signature') and record.get('constructor_signature'):
            return "✅ 已签字"
        else:
            return "⚠️ 待完善"
    
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
    
    def check_current_record(self):
        if not self.current_record_id:
            return
        
        record = db_manager.get_pouring_record_by_id(self.current_record_id)
        if not record:
            return
        
        attachments = db_manager.get_attachments_by_record(self.current_record_id)
        sign_records = db_manager.get_sign_records_by_record(self.current_record_id)
        
        self.issues = export_utils.check_record_issues(record, attachments, sign_records)
        
        self.issue_list.clear()
        
        error_count = 0
        warning_count = 0
        info_count = 0
        
        for issue_type, issue_text in self.issues:
            item = QListWidgetItem()
            
            if issue_type == 'error':
                item.setText(f"❌ 错误: {issue_text}")
                item.setForeground(QColor('#e74c3c'))
                error_count += 1
            elif issue_type == 'warning':
                item.setText(f"⚠️ 警告: {issue_text}")
                item.setForeground(QColor('#f39c12'))
                warning_count += 1
            else:
                item.setText(f"ℹ️ 提示: {issue_text}")
                item.setForeground(QColor('#3498db'))
                info_count += 1
            
            self.issue_list.addItem(item)
        
        image_count = sum(1 for a in attachments if a.get('file_type') == 'image')
        doc_count = sum(1 for a in attachments if a.get('file_type') == 'document')
        
        summary_parts = []
        if error_count > 0:
            summary_parts.append(f'<span style="color:#e74c3c">{error_count}个错误</span>')
        if warning_count > 0:
            summary_parts.append(f'<span style="color:#f39c12">{warning_count}个警告</span>')
        if info_count > 0:
            summary_parts.append(f'<span style="color:#3498db">{info_count}个提示</span>')
        
        summary_text = " | ".join(summary_parts) if summary_parts else '<span style="color:#27ae60">资料完整</span>'
        
        self.summary_label.setText(
            f"{summary_text} | "
            f"照片: {image_count}张 | "
            f"文档: {doc_count}个 | "
            f"附件总数: {len(attachments)}个"
        )
        self.summary_label.setTextFormat(Qt.RichText)
    
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
    
    def generate_default_filename(self, record):
        projects = db_manager.get_all_projects()
        project_name = next((p['name'] for p in projects if p['id'] == record['project_id']), '')
        
        buildings = db_manager.get_buildings_by_project(record['project_id'])
        building_name = next((b['name'] for b in buildings if b['id'] == record['building_id']), '')
        
        safe_project = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_building = "".join(c for c in building_name if c.isalnum() or c in (' ', '-', '_')).strip()
        
        date_str = record['pouring_date']
        location = "".join(c for c in record['component_location'] if c.isalnum() or c in (' ', '-', '_')).strip()
        
        return f"旁站记录_{safe_project}_{safe_building}_{date_str}_{location}.pdf"
    
    def preview_pdf(self):
        if not self.current_record_id:
            QMessageBox.warning(self, "提示", "请先选择一条浇筑记录")
            return
        
        record, attachments, sign_records = self.get_record_full_data(self.current_record_id)
        if not record:
            return
        
        temp_dir = os.path.join(os.path.expanduser("~"), ".concrete_log", "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_file = os.path.join(temp_dir, "preview_" + datetime.now().strftime("%Y%m%d%H%M%S") + ".pdf")
        
        try:
            progress = QProgressDialog("正在生成PDF...", "取消", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
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
        
        default_name = self.generate_default_filename(record)
        
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
        
        for idx, record_id in enumerate(selected_records):
            if progress.wasCanceled():
                break
            
            progress.setValue(idx)
            progress.setLabelText(f"正在导出第 {idx + 1}/{len(selected_records)} 个记录...")
            
            record, attachments, sign_records = self.get_record_full_data(record_id)
            if not record:
                fail_count += 1
                continue
            
            default_name = self.generate_default_filename(record)
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
                            break
            
            self.check_current_record()
    
    def refresh(self):
        self.load_records()
