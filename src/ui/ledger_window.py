import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QMessageBox, QFrame, QSplitter, QTreeWidget, QTreeWidgetItem,
    QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem,
    QFileDialog, QProgressDialog
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QColor, QAction, QDesktopServices
from PySide6.QtCore import QUrl

from src.database import db_manager
from src.utils import export_utils, file_utils


CATEGORY_LABELS = {
    'photo': '📷 照片',
    'ticket': '🧾 小票',
    'delegation': '📋 委托单',
    'draft': '📝 草稿',
    'document': '📄 文档',
    'other': '📦 其他'
}


class LedgerWindow(QWidget):
    record_selected = Signal(int)
    jump_to_edit = Signal(int)
    jump_to_export = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        left_panel = self.create_left_panel()
        right_panel = self.create_right_panel()

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([240, 960])

        main_layout.addWidget(splitter)

    def create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)

        title_label = QLabel("🗂️ 项目筛选")
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

        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("状态:"))
        self.status_filter = QComboBox()
        self.status_filter.addItem("全部状态", None)
        self.status_filter.addItem("⚠️ 资料待完善", "incomplete")
        self.status_filter.addItem("✅ 资料完整", "complete")
        self.status_filter.addItem("📤 已导出", "exported")
        self.status_filter.addItem("📝 未签字", "unsigned")
        self.status_filter.currentIndexChanged.connect(self.on_filter_changed)
        self.status_filter.setStyleSheet("QComboBox { padding: 5px; }")
        status_row.addWidget(self.status_filter, 1)
        filter_layout.addLayout(status_row)

        layout.addLayout(filter_layout)

        tree_title = QLabel("📁 项目结构")
        tree_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #374151; margin-top: 10px;")
        layout.addWidget(tree_title)

        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderLabels(["名称", "数量"])
        self.project_tree.setColumnWidth(0, 160)
        self.project_tree.setColumnWidth(1, 50)
        self.project_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.project_tree.itemClicked.connect(self.on_tree_item_clicked)
        self.project_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                padding: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #dbeafe;
                color: #1e40af;
            }
        """)
        layout.addWidget(self.project_tree, 1)

        return panel

    def create_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)

        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #eef2ff;
                border: 1px solid #c7d2fe;
                border-radius: 10px;
                padding: 12px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setSpacing(6)

        title_row = QHBoxLayout()
        title = QLabel("📊 归档台账视图")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #3730a3;")
        title_row.addWidget(title)
        title_row.addStretch()

        self.stats_label = QLabel("共 0 条记录")
        self.stats_label.setStyleSheet("font-size: 12px; color: #4338ca;")
        title_row.addWidget(self.stats_label)
        header_layout.addLayout(title_row)

        desc = QLabel("汇总展示所有浇筑记录的附件完整度、签字状态和导出情况。双击行可跳转，右键查看更多操作。")
        desc.setStyleSheet("font-size: 12px; color: #6366f1;")
        desc.setWordWrap(True)
        header_layout.addWidget(desc)

        summary_row = QHBoxLayout()
        self.summary_items = {}
        summary_config = [
            ('total', '📋 总记录', '#1f2937'),
            ('complete', '✅ 完整', '#059669'),
            ('incomplete', '⚠️ 待完善', '#d97706'),
            ('unsigned', '📝 未签字', '#dc2626'),
            ('exported', '📤 已导出', '#2563eb'),
        ]
        for key, label_text, color in summary_config:
            item_frame = QFrame()
            item_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: white;
                    border: 1px solid #e0e7ff;
                    border-radius: 6px;
                    padding: 6px 10px;
                }}
            """)
            item_layout = QVBoxLayout(item_frame)
            item_layout.setContentsMargins(8, 4, 8, 4)
            item_layout.setSpacing(0)
            lbl = QLabel("0")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color};")
            item_layout.addWidget(lbl)
            name_lbl = QLabel(label_text)
            name_lbl.setAlignment(Qt.AlignCenter)
            name_lbl.setStyleSheet(f"font-size: 10px; color: {color};")
            item_layout.addWidget(name_lbl)
            summary_row.addWidget(item_frame, 1)
            self.summary_items[key] = lbl

        header_layout.addLayout(summary_row)
        layout.addWidget(header_frame)

        btn_row = QHBoxLayout()

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6;
                color: #374151;
                padding: 8px 16px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #e5e7eb; }
        """)
        refresh_btn.clicked.connect(self.load_data)
        btn_row.addWidget(refresh_btn)

        export_ledger_btn = QPushButton("📋 导出台账Excel")
        export_ledger_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7c3aed; }
        """)
        export_ledger_btn.clicked.connect(self.export_ledger_csv)
        btn_row.addWidget(export_ledger_btn)

        btn_row.addStretch()

        batch_export_btn = QPushButton("📦 批量导出归档包(选中)")
        batch_export_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        batch_export_btn.clicked.connect(self.batch_export_archives)
        btn_row.addWidget(batch_export_btn)

        layout.addLayout(btn_row)

        self.ledger_table = QTableWidget()
        self.ledger_table.setColumnCount(13)
        self.ledger_table.setHorizontalHeaderLabels([
            "选择", "项目", "楼栋", "浇筑日期", "构件部位",
            "📷照片", "🧾小票", "📋委托单", "📝草稿",
            "施工签字", "监理签字", "导出状态", "完整度"
        ])

        header = self.ledger_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)

        self.ledger_table.setColumnWidth(0, 45)
        self.ledger_table.setColumnWidth(1, 100)
        self.ledger_table.setColumnWidth(2, 60)
        self.ledger_table.setColumnWidth(3, 90)
        self.ledger_table.setColumnWidth(4, 160)
        self.ledger_table.setColumnWidth(5, 60)
        self.ledger_table.setColumnWidth(6, 60)
        self.ledger_table.setColumnWidth(7, 65)
        self.ledger_table.setColumnWidth(8, 55)
        self.ledger_table.setColumnWidth(9, 70)
        self.ledger_table.setColumnWidth(10, 70)
        self.ledger_table.setColumnWidth(11, 75)
        self.ledger_table.setColumnWidth(12, 70)

        self.ledger_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ledger_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.ledger_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ledger_table.setAlternatingRowColors(True)
        self.ledger_table.doubleClicked.connect(self.on_row_double_clicked)
        self.ledger_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ledger_table.customContextMenuRequested.connect(self.show_table_context_menu)
        self.ledger_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                gridline-color: #f3f4f6;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #f9fafb;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #e5e7eb;
                font-weight: bold;
                color: #374151;
            }
            QTableWidget::item:selected {
                background-color: #dbeafe;
                color: #1e40af;
            }
        """)
        layout.addWidget(self.ledger_table, 1)

        return panel

    def load_data(self):
        self.load_project_tree()
        self.load_ledger_table()
        self.update_summary_stats()

    def load_project_tree(self):
        self.project_filter.blockSignals(True)
        self.building_filter.blockSignals(True)

        self.project_filter.clear()
        self.project_filter.addItem("全部项目", None)

        self.project_tree.clear()

        projects = db_manager.get_all_projects()
        for project in projects:
            self.project_filter.addItem(project['name'], project['id'])

            project_item = QTreeWidgetItem(self.project_tree, [project['name'], ''])
            project_item.setData(0, Qt.UserRole, ('project', project['id']))
            project_item.setExpanded(True)

            buildings = db_manager.get_buildings_by_project(project['id'])
            total_records = 0
            for building in buildings:
                building_records = db_manager.get_pouring_records(project['id'], building['id'])
                count = len(building_records)
                total_records += count

                building_item = QTreeWidgetItem(project_item, [building['name'], str(count)])
                building_item.setData(0, Qt.UserRole, ('building', building['id']))
                building_item.setForeground(1, QColor('#6b7280'))

            project_item.setText(1, str(total_records))
            project_item.setForeground(1, QColor('#4b5563'))

        self.load_building_filter()

        self.project_filter.blockSignals(False)
        self.building_filter.blockSignals(False)

    def load_building_filter(self):
        self.building_filter.clear()
        self.building_filter.addItem("全部楼栋", None)

        project_id = self.project_filter.currentData()
        if project_id:
            buildings = db_manager.get_buildings_by_project(project_id)
            for building in buildings:
                self.building_filter.addItem(building['name'], building['id'])

    def on_filter_changed(self):
        if self.sender() == self.project_filter:
            self.load_building_filter()
        self.load_ledger_table()
        self.update_summary_stats()

    def on_tree_item_clicked(self, item, column):
        data = item.data(0, Qt.UserRole)
        if not data:
            return

        item_type, item_id = data

        if item_type == 'project':
            for i in range(self.project_filter.count()):
                if self.project_filter.itemData(i) == item_id:
                    self.project_filter.setCurrentIndex(i)
                    break
        elif item_type == 'building':
            parent = item.parent()
            if parent:
                project_data = parent.data(0, Qt.UserRole)
                if project_data:
                    _, project_id = project_data
                    for i in range(self.project_filter.count()):
                        if self.project_filter.itemData(i) == project_id:
                            self.project_filter.setCurrentIndex(i)
                            break
            for i in range(self.building_filter.count()):
                if self.building_filter.itemData(i) == item_id:
                    self.building_filter.setCurrentIndex(i)
                    break

    def get_filtered_stats(self):
        project_id = self.project_filter.currentData()
        building_id = self.building_filter.currentData()
        status_filter = self.status_filter.currentData()

        stats = db_manager.get_record_stats(
            project_id=project_id,
            building_id=building_id
        )

        projects = {p['id']: p['name'] for p in db_manager.get_all_projects()}
        buildings = {}
        for p_id in projects.keys():
            for b in db_manager.get_buildings_by_project(p_id):
                buildings[b['id']] = b['name']

        result = []
        for s in stats:
            s['project_name'] = projects.get(s['project_id'], '')
            s['building_name'] = buildings.get(s['building_id'], '')

            has_photo = (s['photo_count'] or 0) >= 3
            has_ticket = (s['ticket_count'] or 0) >= 1
            has_delegation = (s['delegation_count'] or 0) >= 1
            is_complete = has_photo and has_ticket and has_delegation and s.get('supervisor_signature') and s.get('constructor_signature')

            unsigned = not s.get('supervisor_signature') or not s.get('constructor_signature')
            exported = bool(s.get('exported_at'))

            s['is_complete'] = is_complete
            s['unsigned'] = unsigned
            s['exported'] = exported

            required_total = 5
            complete_items = 0
            if (s['photo_count'] or 0) >= 3:
                complete_items += 2
            elif (s['photo_count'] or 0) > 0:
                complete_items += 1
            if (s['ticket_count'] or 0) > 0:
                complete_items += 1
            if (s['delegation_count'] or 0) > 0:
                complete_items += 1
            if s.get('constructor_signature'):
                complete_items += 0.5
            if s.get('supervisor_signature'):
                complete_items += 0.5
            s['completeness'] = int(complete_items * 100 / required_total)

            if status_filter == 'complete' and not is_complete:
                continue
            if status_filter == 'incomplete' and is_complete:
                continue
            if status_filter == 'exported' and not exported:
                continue
            if status_filter == 'unsigned' and not unsigned:
                continue

            result.append(s)

        return result

    def load_ledger_table(self):
        stats = self.get_filtered_stats()
        self.ledger_table.setRowCount(len(stats))

        for row, s in enumerate(stats):
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            check_item.setCheckState(Qt.Unchecked)
            self.ledger_table.setItem(row, 0, check_item)

            items = [
                (s['project_name'], None),
                (s['building_name'], None),
                (s['pouring_date'], None),
                (s['component_location'], None),
                (str(s['photo_count'] or 0), '#059669' if (s['photo_count'] or 0) >= 3 else ('#d97706' if (s['photo_count'] or 0) > 0 else '#dc2626')),
                (str(s['ticket_count'] or 0), '#059669' if (s['ticket_count'] or 0) >= 1 else '#dc2626'),
                (str(s['delegation_count'] or 0), '#059669' if (s['delegation_count'] or 0) >= 1 else '#dc2626'),
                (str(s['draft_count'] or 0), '#059669' if (s['draft_count'] or 0) > 0 else '#9ca3af'),
                ('✅' if s.get('constructor_signature') else '❌', '#059669' if s.get('constructor_signature') else '#dc2626'),
                ('✅' if s.get('supervisor_signature') else '❌', '#059669' if s.get('supervisor_signature') else '#dc2626'),
                ('📤 ' + s['exported_at'][:10] if s.get('exported_at') else '未导出', '#2563eb' if s.get('exported_at') else '#9ca3af'),
                (f"{s['completeness']}%", '#059669' if s['completeness'] >= 80 else ('#d97706' if s['completeness'] >= 50 else '#dc2626')),
            ]

            for col, (text, color) in enumerate(items):
                item = QTableWidgetItem(text)
                item.setData(Qt.UserRole, s['id'])
                if color:
                    item.setForeground(QColor(color))
                    if text in ('❌', '未导出'):
                        f = item.font()
                        f.setBold(True)
                        item.setFont(f)
                self.ledger_table.setItem(row, col + 1, item)

            completeness = s['completeness']
            if completeness >= 80:
                bg_color = QColor('#f0fdf4')
            elif completeness >= 50:
                bg_color = QColor('#fffbeb')
            else:
                bg_color = QColor('#fef2f2')

            for col in range(self.ledger_table.columnCount()):
                item = self.ledger_table.item(row, col)
                if item:
                    item.setBackground(bg_color)

        self.stats_label.setText(f"共 {len(stats)} 条记录")

    def update_summary_stats(self):
        stats = self.get_filtered_stats()
        self.summary_items['total'].setText(str(len(stats)))
        self.summary_items['complete'].setText(str(sum(1 for s in stats if s['is_complete'])))
        self.summary_items['incomplete'].setText(str(sum(1 for s in stats if not s['is_complete'])))
        self.summary_items['unsigned'].setText(str(sum(1 for s in stats if s['unsigned'])))
        self.summary_items['exported'].setText(str(sum(1 for s in stats if s['exported'])))

    def on_row_double_clicked(self, index):
        item = self.ledger_table.item(index.row(), 1)
        if item:
            record_id = item.data(Qt.UserRole)
            if record_id:
                self.jump_to_edit.emit(record_id)

    def show_table_context_menu(self, position):
        item = self.ledger_table.itemAt(position)
        if not item:
            return

        row = item.row()
        record_id_item = self.ledger_table.item(row, 1)
        if not record_id_item:
            return
        record_id = record_id_item.data(Qt.UserRole)
        if not record_id:
            return

        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)

        edit_action = QAction("✏️ 跳转到日志编排", self)
        edit_action.triggered.connect(lambda: self.jump_to_edit.emit(record_id))
        menu.addAction(edit_action)

        export_action = QAction("📄 跳转到打印导出", self)
        export_action.triggered.connect(lambda: self.jump_to_export.emit(record_id))
        menu.addAction(export_action)

        menu.addSeparator()

        single_export_action = QAction("📦 导出本条归档包", self)
        single_export_action.triggered.connect(lambda: self.export_single_archive(record_id))
        menu.addAction(single_export_action)

        menu.exec(self.ledger_table.viewport().mapToGlobal(position))

    def get_selected_record_ids(self):
        ids = []
        for row in range(self.ledger_table.rowCount()):
            check_item = self.ledger_table.item(row, 0)
            if check_item and check_item.checkState() == Qt.Checked:
                record_item = self.ledger_table.item(row, 1)
                if record_item:
                    rid = record_item.data(Qt.UserRole)
                    if rid:
                        ids.append(rid)
        return ids

    def export_single_archive(self, record_id):
        self._export_archive_batch([record_id])

    def batch_export_archives(self):
        ids = self.get_selected_record_ids()
        if not ids:
            QMessageBox.information(self, "提示", "请先勾选要导出的记录（第一列复选框）")
            return
        self._export_archive_batch(ids)

    def _export_archive_batch(self, record_ids):
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择归档包输出目录",
            os.path.join(os.path.expanduser("~"), "Documents")
        )
        if not dir_path:
            return

        success_count = 0
        fail_count = 0
        errors = []

        progress = QProgressDialog("正在生成归档包...", "取消", 0, len(record_ids), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)

        projects = db_manager.get_all_projects()

        for idx, record_id in enumerate(record_ids):
            if progress.wasCanceled():
                break

            progress.setValue(idx)
            progress.setLabelText(f"正在处理第 {idx + 1}/{len(record_ids)} 个记录...")

            try:
                record = db_manager.get_pouring_record_by_id(record_id)
                if not record:
                    fail_count += 1
                    errors.append(f"记录ID {record_id}: 找不到记录")
                    continue

                attachments = db_manager.get_attachments_by_record(record_id)
                sign_records = db_manager.get_sign_records_by_record(record_id)

                buildings = db_manager.get_buildings_by_project(record['project_id'])

                def sanitize(text):
                    return "".join(c for c in text if c.isalnum() or c in (' ', '-', '_', '号', '楼', '层')).strip() or '未命名'

                project_name = next((p['name'] for p in projects if p['id'] == record['project_id']), '')
                building_name = next((b['name'] for b in buildings if b['id'] == record['building_id']), '')

                folder_name = f"旁站归档_{sanitize(project_name)}_{sanitize(building_name)}_{record['pouring_date']}_{sanitize(record['component_location'])}"
                record_folder = os.path.join(dir_path, folder_name)
                os.makedirs(record_folder, exist_ok=True)

                pdf_filename = export_utils.generate_filename(record, projects, buildings)
                pdf_path = os.path.join(record_folder, pdf_filename)

                record['project_name'] = project_name
                record['building_name'] = building_name
                export_utils.generate_pdf(record, attachments, sign_records, pdf_path)

                if attachments:
                    original_folder = os.path.join(record_folder, "原始附件")
                    os.makedirs(original_folder, exist_ok=True)

                    category_folders = {
                        'photo': '01_现场照片',
                        'ticket': '02_罐车小票',
                        'delegation': '03_试块委托单',
                        'draft': '04_现场草稿',
                        'document': '05_其他文档',
                        'other': '06_其他文件'
                    }

                    import shutil as _shutil
                    for att in attachments:
                        cat = att.get('category', 'other')
                        cat_folder = category_folders.get(cat, '06_其他文件')
                        target_dir = os.path.join(original_folder, cat_folder)
                        os.makedirs(target_dir, exist_ok=True)

                        src = att.get('file_path', '')
                        if src and os.path.exists(src):
                            dest = os.path.join(target_dir, att.get('file_name', ''))
                            counter = 1
                            while os.path.exists(dest):
                                name, ext = os.path.splitext(att.get('file_name', ''))
                                dest = os.path.join(target_dir, f"{name}_{counter}{ext}")
                                counter += 1
                            try:
                                _shutil.copy2(src, dest)
                            except:
                                pass

                manifest_path = os.path.join(record_folder, "归档清单.txt")
                with open(manifest_path, 'w', encoding='utf-8') as mf:
                    mf.write("=" * 60 + "\n")
                    mf.write("  混凝土浇筑旁站归档清单\n")
                    mf.write("=" * 60 + "\n\n")
                    mf.write(f"项目名称: {project_name}\n")
                    mf.write(f"楼栋号: {building_name}\n")
                    mf.write(f"浇筑日期: {record['pouring_date']}\n")
                    mf.write(f"构件部位: {record['component_location']}\n")
                    mf.write(f"施工单位: {record.get('construction_unit', '')}\n")
                    mf.write(f"强度等级: {record.get('strength_grade', '')}\n")
                    mf.write(f"浇筑方量: {record.get('concrete_volume', 0)} m³\n\n")

                    cat_labels = {'photo': '现场照片', 'ticket': '罐车小票', 'delegation': '试块委托单',
                                  'draft': '现场草稿', 'document': '其他文档', 'other': '其他文件'}
                    cat_counts = {}
                    for a in attachments:
                        c = a.get('category', 'other')
                        cat_counts[c] = cat_counts.get(c, 0) + 1

                    mf.write("附件统计:\n")
                    for cat, label in cat_labels.items():
                        mf.write(f"  {label}: {cat_counts.get(cat, 0)} 个\n")
                    mf.write(f"  合计: {len(attachments)} 个\n\n")

                    mf.write(f"施工签字: {'✅' + record.get('constructor_signature', '') if record.get('constructor_signature') else '❌ 未签字'}\n")
                    mf.write(f"监理签字: {'✅' + record.get('supervisor_signature', '') if record.get('supervisor_signature') else '❌ 未签字'}\n\n")
                    mf.write(f"归档生成时间: {db_manager.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

                db_manager.update_record_exported(record_id)
                success_count += 1

            except Exception as e:
                fail_count += 1
                errors.append(f"记录ID {record_id}: {str(e)}")
                import traceback
                traceback.print_exc()

        progress.setValue(len(record_ids))

        self.load_ledger_table()
        self.update_summary_stats()

        msg = f"归档包生成完成！\n\n成功: {success_count} 个\n失败: {fail_count} 个\n\n输出目录: {dir_path}"
        if errors:
            msg += "\n\n错误详情:\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                msg += f"\n...还有 {len(errors) - 10} 个错误"

        QMessageBox.information(self, "批量归档结果", msg)

    def export_ledger_csv(self):
        stats = self.get_filtered_stats()
        if not stats:
            QMessageBox.information(self, "提示", "当前没有数据可导出")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出台账",
            os.path.join(os.path.expanduser("~"), "Documents", f"归档台账_{db_manager.datetime.now().strftime('%Y%m%d')}.csv"),
            "CSV文件 (*.csv)"
        )
        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8-sig') as f:
                header = ["项目", "楼栋", "浇筑日期", "构件部位", "照片数", "小票数",
                          "委托单数", "草稿数", "施工签字", "监理签字", "导出时间", "完整度%"]
                f.write(",".join(header) + "\n")

                for s in stats:
                    row = [
                        s['project_name'], s['building_name'], s['pouring_date'], s['component_location'],
                        str(s['photo_count'] or 0), str(s['ticket_count'] or 0),
                        str(s['delegation_count'] or 0), str(s['draft_count'] or 0),
                        '✅' + (s.get('constructor_signature') or '') if s.get('constructor_signature') else '未签字',
                        '✅' + (s.get('supervisor_signature') or '') if s.get('supervisor_signature') else '未签字',
                        s.get('exported_at') or '未导出',
                        str(s['completeness'])
                    ]
                    f.write(",".join(f'"{x}"' for x in row) + "\n")

            QMessageBox.information(self, "成功", f"台账已导出到：\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出台账失败：{str(e)}")

    def refresh(self):
        self.load_data()
