import os
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QFileDialog, QMessageBox,
    QFrame, QDateEdit, QSplitter, QTreeWidget, QTreeWidgetItem,
    QAbstractItemView, QMenu, QInputDialog, QTabWidget, QSizePolicy
)
from PySide6.QtCore import Qt, QDate, QMimeData, QSize, Signal
from PySide6.QtGui import (
    QDragEnterEvent, QDropEvent, QPixmap, QIcon, QAction, QDrag
)

from src.database import db_manager
from src.utils import file_utils


class DropArea(QFrame):
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.setStyleSheet("""
            DropArea {
                border: 2px dashed #6b7280;
                border-radius: 12px;
                background-color: #fafafa;
                min-height: 140px;
            }
            DropArea:hover {
                border-color: #3b82f6;
                background-color: #eff6ff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        icon_label = QLabel("📁")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 48px;")

        hint_label = QLabel("拖拽文件到此处\n或点击选择文件")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet("font-size: 14px; color: #4b5563;")

        sub_hint = QLabel("支持：照片、罐车小票、试块委托单、现场草稿")
        sub_hint.setAlignment(Qt.AlignCenter)
        sub_hint.setStyleSheet("font-size: 11px; color: #9ca3af;")

        layout.addWidget(icon_label)
        layout.addWidget(hint_label)
        layout.addWidget(sub_hint)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                DropArea {
                    border: 2px solid #3b82f6;
                    border-radius: 12px;
                    background-color: #dbeafe;
                }
            """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            DropArea {
                border: 2px dashed #6b7280;
                border-radius: 12px;
                background-color: #fafafa;
                min-height: 140px;
            }
            DropArea:hover {
                border-color: #3b82f6;
                background-color: #eff6ff;
            }
        """)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                files.append(file_path)
            elif os.path.isdir(file_path):
                for root, dirs, fs in os.walk(file_path):
                    for f in fs:
                        files.append(os.path.join(root, f))

        self.dragLeaveEvent(None)
        if files:
            self.files_dropped.emit(files)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            file_dialog = QFileDialog()
            files, _ = file_dialog.getOpenFileNames(
                self,
                "选择文件",
                "",
                "所有文件 (*.*);;图片 (*.jpg *.jpeg *.png *.bmp *.webp);;文档 (*.doc *.docx *.xls *.xlsx *.pdf)"
            )
            if files:
                self.files_dropped.emit(files)


class AttachmentListWidget(QListWidget):
    def __init__(self, category_key, parent=None):
        super().__init__(parent)
        self.category_key = category_key
        self.setViewMode(QListWidget.IconMode)
        self.setIconSize(QSize(80, 80))
        self.setResizeMode(QListWidget.Adjust)
        self.setSpacing(6)
        self.setMovement(QListWidget.Free)
        self.setUniformItemSizes(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setContextMenuPolicy(Qt.CustomContextMenu)


class ImportWindow(QWidget):
    record_created = Signal(int)

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
        splitter.setSizes([280, 900])

        main_layout.addWidget(splitter)

    def create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)

        title_label = QLabel("📂 项目结构")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1f2937;")
        layout.addWidget(title_label)

        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderLabels(["名称", "类型"])
        self.project_tree.setColumnWidth(0, 180)
        self.project_tree.setColumnWidth(1, 60)
        self.project_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.project_tree.itemClicked.connect(self.on_tree_item_clicked)
        self.project_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.project_tree.customContextMenuRequested.connect(self.show_tree_context_menu)
        self.project_tree.setStyleSheet("""
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
        layout.addWidget(self.project_tree, 1)

        btn_layout = QHBoxLayout()
        add_project_btn = QPushButton("+ 项目")
        add_project_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        add_project_btn.clicked.connect(self.add_project)

        add_building_btn = QPushButton("+ 楼栋")
        add_building_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        add_building_btn.clicked.connect(self.add_building)

        btn_layout.addWidget(add_project_btn)
        btn_layout.addWidget(add_building_btn)
        layout.addLayout(btn_layout)

        return panel

    def create_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)

        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #eff6ff;
                border: 1px solid #bfdbfe;
                border-radius: 10px;
                padding: 12px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(10)

        info_title = QLabel("📝 归档信息")
        info_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #1e40af;")
        info_layout.addWidget(info_title)

        form_layout = QHBoxLayout()

        left_form = QVBoxLayout()
        left_form.setSpacing(6)
        right_form = QVBoxLayout()
        right_form.setSpacing(6)

        left_form.addWidget(QLabel("项目:"))
        self.project_combo = QComboBox()
        self.project_combo.setStyleSheet("QComboBox { padding: 5px; }")
        self.project_combo.currentIndexChanged.connect(self.on_project_changed)
        left_form.addWidget(self.project_combo)

        left_form.addWidget(QLabel("楼栋:"))
        self.building_combo = QComboBox()
        self.building_combo.setStyleSheet("QComboBox { padding: 5px; }")
        left_form.addWidget(self.building_combo)

        left_form.addWidget(QLabel("浇筑日期:"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setStyleSheet("QDateEdit { padding: 5px; }")
        left_form.addWidget(self.date_edit)

        right_form.addWidget(QLabel("构件部位:"))
        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("例如：1#楼地下室负二层墙柱")
        self.location_edit.setStyleSheet("QLineEdit { padding: 5px; }")
        right_form.addWidget(self.location_edit)

        right_form.addWidget(QLabel("浇筑方量 (m³):"))
        self.volume_edit = QLineEdit()
        self.volume_edit.setPlaceholderText("例如：120")
        self.volume_edit.setStyleSheet("QLineEdit { padding: 5px; }")
        right_form.addWidget(self.volume_edit)

        right_form.addWidget(QLabel("罐车数量:"))
        self.truck_edit = QLineEdit()
        self.truck_edit.setPlaceholderText("例如：15")
        self.truck_edit.setStyleSheet("QLineEdit { padding: 5px; }")
        right_form.addWidget(self.truck_edit)

        form_layout.addLayout(left_form, 1)
        form_layout.addLayout(right_form, 1)
        info_layout.addLayout(form_layout)

        btn_row = QHBoxLayout()
        new_record_btn = QPushButton("📝 创建新浇筑记录")
        new_record_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        new_record_btn.clicked.connect(self.create_new_record)
        btn_row.addStretch()
        btn_row.addWidget(new_record_btn)
        info_layout.addLayout(btn_row)

        layout.addWidget(info_frame)

        drop_title = QLabel("📥 资料导入")
        drop_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #1f2937; margin-top: 8px;")
        layout.addWidget(drop_title)

        self.drop_area = DropArea()
        self.drop_area.files_dropped.connect(self.on_files_dropped)
        layout.addWidget(self.drop_area)

        tabs_title_layout = QHBoxLayout()
        tabs_title = QLabel("📂 附件分组查看")
        tabs_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #1f2937; margin-top: 8px;")
        tabs_title_layout.addWidget(tabs_title)
        tabs_title_layout.addStretch()

        self.pending_count_label = QLabel("")
        self.pending_count_label.setStyleSheet("color: #f59e0b; font-size: 12px; font-weight: bold;")
        tabs_title_layout.addWidget(self.pending_count_label)

        layout.addLayout(tabs_title_layout)

        self.attachment_tabs = QTabWidget()
        self.attachment_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #f3f4f6;
                padding: 8px 14px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-bottom: none;
                color: #1d4ed8;
                font-weight: bold;
            }
        """)

        self.category_lists = {}
        for cat_key, cat_info in file_utils.ATTACHMENT_CATEGORIES.items():
            list_widget = AttachmentListWidget(cat_key)
            list_widget.customContextMenuRequested.connect(
                lambda pos, ck=cat_key: self.show_file_context_menu(pos, ck)
            )
            self.attachment_tabs.addTab(list_widget, f"{cat_info['icon']} {cat_info['name']}")
            self.category_lists[cat_key] = list_widget

        layout.addWidget(self.attachment_tabs, 1)

        file_btn_layout = QHBoxLayout()
        import_btn = QPushButton("📥 导入待处理文件")
        import_btn.setStyleSheet("""
            QPushButton {
                background-color: #16a34a;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #15803d;
            }
        """)
        import_btn.clicked.connect(self.import_all_pending)

        delete_btn = QPushButton("🗑️ 删除选中")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #b91c1c;
            }
        """)
        delete_btn.clicked.connect(self.remove_selected_files)

        clear_btn = QPushButton("清空待处理")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #6b7280;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
        """)
        clear_btn.clicked.connect(self.clear_pending_files)

        file_btn_layout.addStretch()
        file_btn_layout.addWidget(clear_btn)
        file_btn_layout.addWidget(delete_btn)
        file_btn_layout.addWidget(import_btn)
        layout.addLayout(file_btn_layout)

        return panel

    def load_projects(self):
        self.project_combo.clear()
        self.project_tree.clear()

        projects = db_manager.get_all_projects()
        for project in projects:
            self.project_combo.addItem(project['name'], project['id'])

            project_item = QTreeWidgetItem(self.project_tree, [project['name'], '项目'])
            project_item.setData(0, Qt.UserRole, ('project', project['id']))
            project_item.setIcon(0, QIcon.fromTheme("folder"))

            buildings = db_manager.get_buildings_by_project(project['id'])
            for building in buildings:
                building_item = QTreeWidgetItem(project_item, [building['name'], '楼栋'])
                building_item.setData(0, Qt.UserRole, ('building', building['id']))
                building_item.setIcon(0, QIcon.fromTheme("folder"))

                records = db_manager.get_pouring_records(project['id'], building['id'])
                for record in records:
                    display_text = f"{record['pouring_date']} - {record['component_location']}"
                    record_item = QTreeWidgetItem(building_item, [display_text, '记录'])
                    record_item.setData(0, Qt.UserRole, ('record', record['id']))
                    record_item.setIcon(0, QIcon.fromTheme("text-x-generic"))

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

    def clear_all_tabs(self):
        for cat_key, list_widget in self.category_lists.items():
            list_widget.clear()

    def load_attachments(self, record_id):
        self.pending_files = []
        self.pending_count_label.setText("")
        self.clear_all_tabs()

        attachments = db_manager.get_attachments_by_record(record_id)
        for att in attachments:
            self.add_existing_attachment_to_tab(att)

    def add_existing_attachment_to_tab(self, attachment):
        cat_key = attachment.get('category', 'other')
        list_widget = self.category_lists.get(cat_key, self.category_lists['other'])
        self._add_attachment_item(list_widget, attachment['file_path'], ('existing', attachment['id'], attachment))

    def add_pending_file_to_tab(self, file_path):
        cat_key = file_utils.classify_attachment(file_path)
        list_widget = self.category_lists.get(cat_key, self.category_lists['other'])
        self._add_attachment_item(list_widget, file_path, ('pending', None, {'file_path': file_path}))

    def _add_attachment_item(self, list_widget, file_path, user_data):
        item = QListWidgetItem()
        item.setData(Qt.UserRole, user_data)

        file_name = os.path.basename(file_path)
        status_type = user_data[0]

        if os.path.exists(file_path):
            file_type = file_utils.get_file_type(file_path)
            if file_type == 'image':
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    icon = QIcon(pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    item.setIcon(icon)

            size = os.path.getsize(file_path)
            size_str = file_utils.format_file_size(size)
        else:
            size_str = "文件不存在"

        if status_type == 'pending':
            cat_info = file_utils.get_category_info(list_widget.category_key)
            item.setText(f"⏳ {cat_info['icon']} {file_name[:15]}")
            item.setToolTip(f"[待导入] {file_name} ({size_str})")
            item.setForeground(Qt.darkYellow)
        else:
            att_data = user_data[2]
            section_ref = att_data.get('section_ref', '')
            section_text = ''
            if section_ref:
                section_names = {
                    'basic_info': '基本信息',
                    'personnel': '人员设备',
                    'inspection': '检查情况',
                    'handling': '处理意见'
                }
                section_text = f"[{section_names.get(section_ref, section_ref)}]"
            cat_info = file_utils.get_category_info(list_widget.category_key)
            item.setText(f"{cat_info['icon']} {file_name[:15]}")
            item.setToolTip(f"{file_name} ({size_str}) {section_text}")

        item.setSizeHint(QSize(110, 120))
        list_widget.addItem(item)

    def on_files_dropped(self, files):
        added = 0
        for file_path in files:
            if file_path not in self.pending_files:
                self.pending_files.append(file_path)
                self.add_pending_file_to_tab(file_path)
                added += 1

        if added > 0:
            self.update_pending_count()
            QMessageBox.information(self, "提示", f"已添加 {added} 个文件到待处理列表，点击『导入待处理文件』保存到记录中。")

    def update_pending_count(self):
        if self.pending_files:
            self.pending_count_label.setText(f"⏳ 待导入: {len(self.pending_files)} 个文件")
        else:
            self.pending_count_label.setText("")

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
            add_building_action = QAction("➕ 添加楼栋", self)
            add_building_action.triggered.connect(lambda: self.add_building_for_project(item_id))
            menu.addAction(add_building_action)

        elif item_type == 'building':
            add_record_action = QAction("➕ 添加浇筑记录", self)
            add_record_action.triggered.connect(lambda: self.select_building_for_record(item_id))
            menu.addAction(add_record_action)

        elif item_type == 'record':
            delete_action = QAction("🗑️ 删除记录", self)
            delete_action.triggered.connect(lambda: self.delete_record(item_id))
            menu.addAction(delete_action)

        menu.exec(self.project_tree.viewport().mapToGlobal(position))

    def show_file_context_menu(self, position, category_key):
        list_widget = self.category_lists[category_key]
        item = list_widget.itemAt(position)
        if not item:
            return

        data = item.data(Qt.UserRole)
        if not data:
            return

        status_type = data[0]
        menu = QMenu(self)

        if status_type == 'existing':
            attachment_id = data[1]
            att_data = data[2]

            rename_cat_menu = QMenu("🔄 更改分类", self)
            for cat_key, cat_info in file_utils.ATTACHMENT_CATEGORIES.items():
                action = QAction(f"{cat_info['icon']} {cat_info['name']}", self)
                action.triggered.connect(lambda checked, aid=attachment_id, ck=cat_key: self.change_category(aid, ck))
                rename_cat_menu.addAction(action)
            menu.addMenu(rename_cat_menu)

            set_section_menu = QMenu("📎 分配到段落", self)
            sections = [
                ('basic_info', '基本信息'),
                ('personnel', '人员设备'),
                ('inspection', '检查情况'),
                ('handling', '处理意见')
            ]
            for section_key, section_name in sections:
                action = QAction(section_name, self)
                action.triggered.connect(lambda checked, aid=attachment_id, sk=section_key: self.assign_section(aid, sk))
                set_section_menu.addAction(action)

            clear_section_action = QAction("❌ 取消分配", self)
            clear_section_action.triggered.connect(lambda: self.assign_section(attachment_id, ''))
            set_section_menu.addAction(clear_section_action)
            menu.addMenu(set_section_menu)

            desc_action = QAction("✏️ 修改说明", self)
            desc_action.triggered.connect(lambda: self.edit_description(attachment_id, att_data.get('description', '')))
            menu.addAction(desc_action)

        preview_action = QAction("👁️ 打开预览", self)
        preview_action.triggered.connect(lambda: os.startfile(data[2]['file_path']))
        menu.addAction(preview_action)

        delete_action = QAction("🗑️ 删除选中", self)
        delete_action.triggered.connect(self.remove_selected_files)
        menu.addAction(delete_action)

        menu.exec(list_widget.viewport().mapToGlobal(position))

    def change_category(self, attachment_id, category_key):
        db_manager.update_attachment_category(attachment_id, category_key)
        if self.current_record_id:
            self.load_attachments(self.current_record_id)

    def assign_section(self, attachment_id, section_ref):
        db_manager.update_attachment_section(attachment_id, section_ref)
        if self.current_record_id:
            self.load_attachments(self.current_record_id)

    def edit_description(self, attachment_id, current_desc):
        text, ok = QInputDialog.getText(self, "修改说明", "请输入附件说明:", text=current_desc)
        if ok:
            db_manager.update_attachment_description(attachment_id, text)
            if self.current_record_id:
                self.load_attachments(self.current_record_id)

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

    def select_building_for_record(self, building_id):
        for i in range(self.building_combo.count()):
            if self.building_combo.itemData(i) == building_id:
                self.building_combo.setCurrentIndex(i)
                break
        self.location_edit.setFocus()

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
            self.clear_all_tabs()

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
            self.pending_files = []

        QMessageBox.information(self, "成功", "浇筑记录创建成功！")
        self.load_projects()
        self.load_attachments(record_id)
        self.update_pending_count()
        self.record_created.emit(record_id)

    def import_all_pending(self):
        if not self.current_record_id:
            QMessageBox.warning(self, "提示", "请先创建或选择一条浇筑记录")
            return

        if not self.pending_files:
            QMessageBox.warning(self, "提示", "没有待导入的文件")
            return

        self.import_files_to_record(self.current_record_id, self.pending_files)
        self.pending_files = []
        self.load_attachments(self.current_record_id)
        self.update_pending_count()
        QMessageBox.information(self, "成功", f"成功导入所有待处理文件！")

    def import_files_to_record(self, record_id, files):
        for file_path in files:
            if not os.path.exists(file_path):
                continue

            file_type = file_utils.get_file_type(file_path)
            category = file_utils.classify_attachment(file_path)
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
                    'section_ref': '',
                    'category': category
                }
                db_manager.add_attachment(attachment_data)

    def remove_selected_files(self):
        for cat_key, list_widget in self.category_lists.items():
            items = list_widget.selectedItems()
            for item in items:
                data = item.data(Qt.UserRole)
                if not data:
                    continue

                status_type = data[0]

                if status_type == 'pending':
                    file_path = data[2]['file_path']
                    if file_path in self.pending_files:
                        self.pending_files.remove(file_path)
                    list_widget.takeItem(list_widget.row(item))

                elif status_type == 'existing':
                    attachment_id = data[1]
                    confirm = QMessageBox.question(
                        self, "确认删除",
                        f"确定要删除这个附件吗？",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if confirm == QMessageBox.Yes:
                        db_manager.delete_attachment(attachment_id)
                        list_widget.takeItem(list_widget.row(item))

        self.update_pending_count()

    def clear_pending_files(self):
        if not self.pending_files:
            return

        confirm = QMessageBox.question(
            self, "确认清空",
            f"确定要清空所有待处理的 {len(self.pending_files)} 个文件吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.pending_files = []
            if self.current_record_id:
                self.load_attachments(self.current_record_id)
            else:
                self.clear_all_tabs()
            self.update_pending_count()
