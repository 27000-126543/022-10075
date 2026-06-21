import os
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QFileDialog, QMessageBox,
    QFrame, QDateEdit, QSplitter, QTreeWidget, QTreeWidgetItem,
    QAbstractItemView, QMenu, QInputDialog
)
from PySide6.QtCore import Qt, QDate, QMimeData, QSize
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QIcon, QAction

from src.database import db_manager
from src.utils import file_utils


class DropArea(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.setStyleSheet("""
            DropArea {
                border: 2px dashed #999;
                border-radius: 10px;
                background-color: #fafafa;
                min-height: 150px;
            }
            DropArea:hover {
                border-color: #4a90e2;
                background-color: #f0f7ff;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        icon_label = QLabel("📁")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 48px;")
        
        hint_label = QLabel("拖拽文件到此处\n或点击选择文件")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet("font-size: 14px; color: #666;")
        
        layout.addWidget(icon_label)
        layout.addWidget(hint_label)
        
        self.files = []
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                self.files.append(file_path)
            elif os.path.isdir(file_path):
                for root, dirs, files in os.walk(file_path):
                    for f in files:
                        self.files.append(os.path.join(root, f))
        
        self.parent().on_files_dropped(self.files)
        self.files = []
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            file_dialog = QFileDialog()
            files, _ = file_dialog.getOpenFileNames(
                self,
                "选择文件",
                "",
                "所有文件 (*.*);;图片 (*.jpg *.jpeg *.png *.bmp);;文档 (*.doc *.docx *.xls *.xlsx *.pdf)"
            )
            if files:
                self.parent().on_files_dropped(files)


class ImportWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_record_id = None
        self.pending_files = []
        self.init_ui()
        self.load_projects()
    
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
        
        title_label = QLabel("项目结构")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title_label)
        
        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderLabels(["项目 / 楼栋 / 记录"])
        self.project_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.project_tree.itemClicked.connect(self.on_tree_item_clicked)
        self.project_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.project_tree.customContextMenuRequested.connect(self.show_tree_context_menu)
        layout.addWidget(self.project_tree, 1)
        
        btn_layout = QHBoxLayout()
        add_project_btn = QPushButton("+ 新建项目")
        add_project_btn.clicked.connect(self.add_project)
        add_building_btn = QPushButton("+ 新建楼栋")
        add_building_btn.clicked.connect(self.add_building)
        btn_layout.addWidget(add_project_btn)
        btn_layout.addWidget(add_building_btn)
        layout.addLayout(btn_layout)
        
        return panel
    
    def create_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.StyledPanel)
        info_layout = QVBoxLayout(info_frame)
        
        info_title = QLabel("归档信息")
        info_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        info_layout.addWidget(info_title)
        
        form_layout = QHBoxLayout()
        
        left_form = QVBoxLayout()
        right_form = QVBoxLayout()
        
        left_form.addWidget(QLabel("项目:"))
        self.project_combo = QComboBox()
        self.project_combo.currentIndexChanged.connect(self.on_project_changed)
        left_form.addWidget(self.project_combo)
        
        left_form.addWidget(QLabel("楼栋:"))
        self.building_combo = QComboBox()
        left_form.addWidget(self.building_combo)
        
        left_form.addWidget(QLabel("浇筑日期:"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        left_form.addWidget(self.date_edit)
        
        right_form.addWidget(QLabel("构件部位:"))
        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("例如：1#楼地下室负二层墙柱")
        right_form.addWidget(self.location_edit)
        
        right_form.addWidget(QLabel("浇筑方量 (m³):"))
        self.volume_edit = QLineEdit()
        self.volume_edit.setPlaceholderText("例如：120")
        right_form.addWidget(self.volume_edit)
        
        right_form.addWidget(QLabel("罐车数量:"))
        self.truck_edit = QLineEdit()
        self.truck_edit.setPlaceholderText("例如：15")
        right_form.addWidget(self.truck_edit)
        
        form_layout.addLayout(left_form, 1)
        form_layout.addLayout(right_form, 1)
        info_layout.addLayout(form_layout)
        
        new_record_btn = QPushButton("📝 创建新浇筑记录")
        new_record_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                padding: 10px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)
        new_record_btn.clicked.connect(self.create_new_record)
        info_layout.addWidget(new_record_btn)
        
        layout.addWidget(info_frame)
        
        drop_label = QLabel("资料导入")
        drop_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(drop_label)
        
        self.drop_area = DropArea(self)
        layout.addWidget(self.drop_area)
        
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self.show_file_context_menu)
        self.file_list.setIconSize(QSize(64, 64))
        layout.addWidget(self.file_list, 1)
        
        file_btn_layout = QHBoxLayout()
        import_btn = QPushButton("📥 导入选中文件")
        import_btn.clicked.connect(self.import_selected_files)
        delete_btn = QPushButton("🗑️ 移除选中文件")
        delete_btn.clicked.connect(self.remove_selected_files)
        clear_btn = QPushButton("清空列表")
        clear_btn.clicked.connect(self.clear_file_list)
        
        file_btn_layout.addWidget(import_btn)
        file_btn_layout.addWidget(delete_btn)
        file_btn_layout.addWidget(clear_btn)
        layout.addLayout(file_btn_layout)
        
        return panel
    
    def load_projects(self):
        self.project_combo.clear()
        self.project_tree.clear()
        
        projects = db_manager.get_all_projects()
        for project in projects:
            self.project_combo.addItem(project['name'], project['id'])
            
            project_item = QTreeWidgetItem(self.project_tree, [project['name']])
            project_item.setData(0, Qt.UserRole, ('project', project['id']))
            
            buildings = db_manager.get_buildings_by_project(project['id'])
            for building in buildings:
                building_item = QTreeWidgetItem(project_item, [building['name']])
                building_item.setData(0, Qt.UserRole, ('building', building['id']))
                
                records = db_manager.get_pouring_records(project['id'], building['id'])
                for record in records:
                    display_text = f"{record['pouring_date']} - {record['component_location']}"
                    record_item = QTreeWidgetItem(building_item, [display_text])
                    record_item.setData(0, Qt.UserRole, ('record', record['id']))
                    record_item.setIcon(0, QIcon.fromTheme("document"))
        
        self.project_tree.expandAll()
        self.load_buildings()
    
    def load_buildings(self):
        self.building_combo.clear()
        project_id = self.project_combo.currentData()
        if project_id:
            buildings = db_manager.get_buildings_by_project(project_id)
            for building in buildings:
                self.building_combo.addItem(building['name'], building['id'])
    
    def on_project_changed(self):
        self.load_buildings()
    
    def on_tree_item_clicked(self, item, column):
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        
        item_type, item_id = data
        
        if item_type == 'project':
            for i in range(self.project_combo.count()):
                if self.project_combo.itemData(i) == item_id:
                    self.project_combo.setCurrentIndex(i)
                    break
        
        elif item_type == 'building':
            parent = item.parent()
            if parent:
                project_data = parent.data(0, Qt.UserRole)
                if project_data:
                    _, project_id = project_data
                    for i in range(self.project_combo.count()):
                        if self.project_combo.itemData(i) == project_id:
                            self.project_combo.setCurrentIndex(i)
                            break
            
            for i in range(self.building_combo.count()):
                if self.building_combo.itemData(i) == item_id:
                    self.building_combo.setCurrentIndex(i)
                    break
        
        elif item_type == 'record':
            self.current_record_id = item_id
            record = db_manager.get_pouring_record_by_id(item_id)
            if record:
                self.load_record_to_form(record)
                self.load_attachments(item_id)
    
    def load_record_to_form(self, record):
        for i in range(self.project_combo.count()):
            if self.project_combo.itemData(i) == record['project_id']:
                self.project_combo.setCurrentIndex(i)
                break
        
        for i in range(self.building_combo.count()):
            if self.building_combo.itemData(i) == record['building_id']:
                self.building_combo.setCurrentIndex(i)
                break
        
        if record['pouring_date']:
            date = QDate.fromString(record['pouring_date'], "yyyy-MM-dd")
            self.date_edit.setDate(date)
        
        self.location_edit.setText(record['component_location'])
        self.volume_edit.setText(str(record['concrete_volume']) if record['concrete_volume'] else "")
        self.truck_edit.setText(str(record['truck_count']) if record['truck_count'] else "")
    
    def load_attachments(self, record_id):
        self.pending_files = []
        self.file_list.clear()
        
        attachments = db_manager.get_attachments_by_record(record_id)
        for att in attachments:
            self.add_file_to_list(att['file_path'], att)
    
    def on_files_dropped(self, files):
        for file_path in files:
            if file_path not in self.pending_files:
                self.pending_files.append(file_path)
                self.add_file_to_list(file_path)
    
    def add_file_to_list(self, file_path, attachment_data=None):
        item = QListWidgetItem()
        
        file_name = os.path.basename(file_path)
        file_type = file_utils.get_file_type(file_path)
        
        if file_type == 'image' and os.path.exists(file_path):
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                icon = QIcon(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                item.setIcon(icon)
        
        type_icon = "🖼️" if file_type == 'image' else "📄" if file_type == 'document' else "📎"
        
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            size_str = file_utils.format_file_size(size)
        else:
            size_str = "文件不存在"
        
        if attachment_data:
            if attachment_data.get('section_ref'):
                section_names = {
                    'basic_info': '基本信息',
                    'personnel': '人员设备',
                    'inspection': '检查情况',
                    'handling': '处理意见'
                }
                section_name = section_names.get(attachment_data['section_ref'], attachment_data['section_ref'])
                item.setText(f"{type_icon} {file_name} ({size_str}) [{section_name}]")
            else:
                item.setText(f"{type_icon} {file_name} ({size_str})")
            item.setData(Qt.UserRole, ('existing', attachment_data['id'], file_path))
        else:
            item.setText(f"{type_icon} {file_name} ({size_str}) [待导入]")
            item.setData(Qt.UserRole, ('pending', None, file_path))
        
        self.file_list.addItem(item)
    
    def show_tree_context_menu(self, position):
        item = self.project_tree.itemAt(position)
        if not item:
            return
        
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        
        item_type, item_id = data
        
        menu = QMenu(self)
        
        if item_type == 'project':
            add_building_action = QAction("添加楼栋", self)
            add_building_action.triggered.connect(lambda: self.add_building_for_project(item_id))
            menu.addAction(add_building_action)
            
            delete_action = QAction("删除项目", self)
            delete_action.triggered.connect(lambda: self.delete_project(item_id))
            menu.addAction(delete_action)
        
        elif item_type == 'building':
            add_record_action = QAction("添加浇筑记录", self)
            add_record_action.triggered.connect(lambda: self.add_record_for_building(item_id))
            menu.addAction(add_record_action)
            
            delete_action = QAction("删除楼栋", self)
            delete_action.triggered.connect(lambda: self.delete_building(item_id))
            menu.addAction(delete_action)
        
        elif item_type == 'record':
            delete_action = QAction("删除记录", self)
            delete_action.triggered.connect(lambda: self.delete_record(item_id))
            menu.addAction(delete_action)
        
        menu.exec(self.project_tree.viewport().mapToGlobal(position))
    
    def show_file_context_menu(self, position):
        items = self.file_list.selectedItems()
        if not items:
            return
        
        menu = QMenu(self)
        
        set_section_menu = QMenu("分配到段落", self)
        
        sections = [
            ('basic_info', '基本信息'),
            ('personnel', '人员设备'),
            ('inspection', '检查情况'),
            ('handling', '处理意见')
        ]
        
        for section_key, section_name in sections:
            action = QAction(section_name, self)
            action.triggered.connect(lambda checked, sk=section_key: self.set_attachment_section(sk))
            set_section_menu.addAction(action)
        
        menu.addMenu(set_section_menu)
        
        preview_action = QAction("预览", self)
        preview_action.triggered.connect(self.preview_file)
        menu.addAction(preview_action)
        
        menu.exec(self.file_list.viewport().mapToGlobal(position))
    
    def set_attachment_section(self, section_key):
        items = self.file_list.selectedItems()
        for item in items:
            data = item.data(Qt.UserRole)
            if data and data[0] == 'existing':
                attachment_id = data[1]
                db_manager.update_attachment_section(attachment_id, section_key)
        
        if self.current_record_id:
            self.load_attachments(self.current_record_id)
    
    def preview_file(self):
        items = self.file_list.selectedItems()
        if not items:
            return
        
        data = items[0].data(Qt.UserRole)
        if not data:
            return
        
        file_path = data[2]
        if os.path.exists(file_path):
            os.startfile(file_path)
    
    def add_project(self):
        name, ok = QInputDialog.getText(self, "新建项目", "请输入项目名称:")
        if ok and name.strip():
            db_manager.add_project(name.strip())
            self.load_projects()
    
    def add_building(self):
        project_id = self.project_combo.currentData()
        if not project_id:
            QMessageBox.warning(self, "提示", "请先选择项目")
            return
        
        name, ok = QInputDialog.getText(self, "新建楼栋", "请输入楼栋名称:")
        if ok and name.strip():
            db_manager.add_building(project_id, name.strip())
            self.load_projects()
            self.load_buildings()
    
    def add_building_for_project(self, project_id):
        name, ok = QInputDialog.getText(self, "新建楼栋", "请输入楼栋名称:")
        if ok and name.strip():
            db_manager.add_building(project_id, name.strip())
            self.load_projects()
    
    def add_record_for_building(self, building_id):
        pass
    
    def delete_project(self, project_id):
        confirm = QMessageBox.question(
            self, "确认删除",
            "删除项目将同时删除该项目下所有楼栋和记录，是否继续？",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.load_projects()
    
    def delete_building(self, building_id):
        confirm = QMessageBox.question(
            self, "确认删除",
            "删除楼栋将同时删除该楼栋下所有记录，是否继续？",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.load_projects()
    
    def delete_record(self, record_id):
        confirm = QMessageBox.question(
            self, "确认删除",
            "确定要删除这条浇筑记录吗？相关附件也将被删除。",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            db_manager.delete_pouring_record(record_id)
            self.load_projects()
            self.current_record_id = None
            self.file_list.clear()
    
    def create_new_record(self):
        project_id = self.project_combo.currentData()
        building_id = self.building_combo.currentData()
        pouring_date = self.date_edit.date().toString("yyyy-MM-dd")
        component_location = self.location_edit.text().strip()
        
        if not project_id:
            QMessageBox.warning(self, "提示", "请选择项目")
            return
        if not building_id:
            QMessageBox.warning(self, "提示", "请选择楼栋")
            return
        if not component_location:
            QMessageBox.warning(self, "提示", "请输入构件部位")
            return
        
        try:
            volume = float(self.volume_edit.text()) if self.volume_edit.text() else 0
        except ValueError:
            QMessageBox.warning(self, "提示", "浇筑方量必须是数字")
            return
        
        try:
            truck_count = int(self.truck_edit.text()) if self.truck_edit.text() else 0
        except ValueError:
            QMessageBox.warning(self, "提示", "罐车数量必须是整数")
            return
        
        record_data = {
            'project_id': project_id,
            'building_id': building_id,
            'pouring_date': pouring_date,
            'component_location': component_location,
            'concrete_volume': volume,
            'truck_count': truck_count
        }
        
        record_id = db_manager.add_pouring_record(record_data)
        self.current_record_id = record_id
        
        if self.pending_files:
            self.import_files_to_record(record_id, self.pending_files)
        
        QMessageBox.information(self, "成功", "浇筑记录创建成功！")
        self.load_projects()
        self.pending_files = []
    
    def import_selected_files(self):
        if not self.current_record_id:
            QMessageBox.warning(self, "提示", "请先创建或选择一条浇筑记录")
            return
        
        selected_files = []
        for item in self.file_list.selectedItems():
            data = item.data(Qt.UserRole)
            if data and data[0] == 'pending':
                selected_files.append(data[2])
        
        if not selected_files:
            QMessageBox.warning(self, "提示", "请选择待导入的文件")
            return
        
        self.import_files_to_record(self.current_record_id, selected_files)
        
        for f in selected_files:
            if f in self.pending_files:
                self.pending_files.remove(f)
        
        self.load_attachments(self.current_record_id)
        QMessageBox.information(self, "成功", f"成功导入 {len(selected_files)} 个文件")
    
    def import_files_to_record(self, record_id, files):
        for file_path in files:
            if not os.path.exists(file_path):
                continue
            
            file_type = file_utils.get_file_type(file_path)
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            
            dest_path = file_utils.copy_to_storage(file_path, record_id, file_type)
            
            if dest_path:
                attachment_data = {
                    'record_id': record_id,
                    'file_name': file_name,
                    'file_path': dest_path,
                    'file_type': file_type,
                    'file_size': file_size,
                    'description': '',
                    'section_ref': ''
                }
                db_manager.add_attachment(attachment_data)
    
    def remove_selected_files(self):
        items = self.file_list.selectedItems()
        for item in items:
            data = item.data(Qt.UserRole)
            if data:
                if data[0] == 'pending':
                    file_path = data[2]
                    if file_path in self.pending_files:
                        self.pending_files.remove(file_path)
                    self.file_list.takeItem(self.file_list.row(item))
                elif data[0] == 'existing':
                    attachment_id = data[1]
                    confirm = QMessageBox.question(
                        self, "确认删除",
                        f"确定要删除附件 {data[2]} 吗？",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if confirm == QMessageBox.Yes:
                        db_manager.delete_attachment(attachment_id)
                        self.file_list.takeItem(self.file_list.row(item))
    
    def clear_file_list(self):
        self.pending_files = []
        if self.current_record_id:
            self.load_attachments(self.current_record_id)
        else:
            self.file_list.clear()
