import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QTextEdit, QFrame, QSplitter, QListWidget, QListWidgetItem,
    QMessageBox, QScrollArea, QGridLayout, QDateTimeEdit,
    QAbstractItemView, QMenu, QInputDialog
)
from PySide6.QtCore import Qt, QDateTime, QMimeData, QSize, QPoint, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPalette, QColor
from PySide6.QtGui import (
    QDragEnterEvent, QDropEvent, QPixmap, QIcon, QDrag, QAction
)

from src.database import db_manager
from src.models.models import STRENGTH_GRADES, WEATHER_OPTIONS, COMMON_CONSTRUCTION_UNITS


class ImageThumbWidget(QWidget):
    removed = Signal(int)

    def __init__(self, attachment, parent=None):
        super().__init__(parent)
        self.attachment = attachment
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        img_label = QLabel()
        pixmap = QPixmap(self.attachment['file_path'])
        if pixmap.isNull():
            img_label.setText("🖼️")
            img_label.setAlignment(Qt.AlignCenter)
            img_label.setStyleSheet("font-size: 32px;")
        else:
            scaled = pixmap.scaled(70, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            img_label.setPixmap(scaled)
        img_label.setAlignment(Qt.AlignCenter)
        img_label.setToolTip(self.attachment.get('description', '') or self.attachment['file_name'])
        img_label.setStyleSheet("""
            QLabel {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 2px;
                background-color: white;
            }
        """)
        img_label.setCursor(Qt.PointingHandCursor)
        img_label.mouseDoubleClickEvent = lambda e: os.startfile(self.attachment['file_path'])
        self.img_label = img_label
        layout.addWidget(img_label)

        name_label = QLabel(self.attachment['file_name'][:10] + "..." if len(self.attachment['file_name']) > 10 else self.attachment['file_name'])
        name_label.setStyleSheet("font-size: 10px; color: #555;")
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        self.setStyleSheet("""
            ImageThumbWidget {
                background-color: #f0f7ff;
                border-radius: 6px;
            }
            ImageThumbWidget:hover {
                background-color: #dbeafe;
            }
        """)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        remove_action = QAction("🗑️ 从此段落移除", self)
        remove_action.triggered.connect(lambda: self.removed.emit(self.attachment['id']))
        menu.addAction(remove_action)

        preview_action = QAction("👁️ 打开预览", self)
        preview_action.triggered.connect(lambda: os.startfile(self.attachment['file_path']))
        menu.addAction(preview_action)

        menu.exec(event.globalPos())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            mime_data = QMimeData()
            mime_data.setData('application/x-attachment-id', str(self.attachment['id']).encode())
            mime_data.setText(f"attachment:{self.attachment['id']}")

            drag = QDrag(self)
            drag.setMimeData(mime_data)

            pixmap = self.img_label.pixmap()
            if pixmap and not pixmap.isNull():
                drag.setPixmap(pixmap)
                drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))

            drag.exec(Qt.CopyAction | Qt.MoveAction)


class DropZone(QFrame):
    imageDropped = Signal(int, int)
    imageRemoved = Signal(int)

    def __init__(self, section_key, section_name, parent=None):
        super().__init__(parent)
        self.section_key = section_key
        self.section_name = section_name
        self.attachments = []
        self.edit_window = None
        self.setAcceptDrops(True)
        self.init_ui()

    def init_ui(self):
        self.setMinimumHeight(100)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            DropZone {
                border: 2px dashed #9ca3af;
                border-radius: 10px;
                background-color: #fafafa;
            }
            DropZone:hover {
                border-color: #4a90e2;
                background-color: #f0f7ff;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        header_layout = QHBoxLayout()
        icon_label = QLabel("📎")
        icon_label.setStyleSheet("font-size: 16px;")
        header_layout.addWidget(icon_label)

        title_label = QLabel(f"拖拽照片到此处 - {self.section_name}")
        title_label.setStyleSheet("color: #4b5563; font-size: 12px; font-weight: bold;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        header_layout.addWidget(self.count_label)

        main_layout.addLayout(header_layout)

        self.images_container = QWidget()
        self.images_layout = QHBoxLayout(self.images_container)
        self.images_layout.setContentsMargins(0, 0, 0, 0)
        self.images_layout.setSpacing(6)
        self.images_layout.setAlignment(Qt.AlignLeft)
        main_layout.addWidget(self.images_container, 1)

    def set_edit_window(self, window):
        self.edit_window = window

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasFormat('application/x-attachment-id'):
            event.acceptProposedAction()
            self.setStyleSheet("""
                DropZone {
                    border: 2px dashed #4a90e2;
                    border-radius: 10px;
                    background-color: #dbeafe;
                }
            """)

    def dragLeaveEvent(self, event):
        self.update_display()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat('application/x-attachment-id'):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        raw = event.mimeData().data('application/x-attachment-id')
        if raw:
            try:
                attachment_id = int(bytes(raw).decode())
                db_manager.update_attachment_section(attachment_id, self.section_key)
                if self.edit_window:
                    self.edit_window.reload_all()
                event.acceptProposedAction()
            except ValueError:
                pass
        self.update_display()

    def add_attachment(self, attachment):
        self.attachments.append(attachment)
        self.update_display()

    def clear_attachments(self):
        self.attachments = []
        self.update_display()

    def remove_attachment(self, attachment_id):
        self.attachments = [a for a in self.attachments if a['id'] != attachment_id]
        db_manager.update_attachment_section(attachment_id, '')
        self.update_display()
        if self.edit_window:
            self.edit_window.reload_attachments()

    def update_display(self):
        while self.images_layout.count():
            child = self.images_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for att in self.attachments:
            thumb = ImageThumbWidget(att)
            thumb.removed.connect(self.remove_attachment)
            self.images_layout.addWidget(thumb)

        if not self.attachments:
            placeholder = QLabel("将照片拖放到这里，点击照片还可以拖到其他段落")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("color: #9ca3af; font-size: 11px;")
            self.images_layout.addWidget(placeholder)

        if self.attachments:
            self.setStyleSheet("""
                DropZone {
                    border: 2px solid #4a90e2;
                    border-radius: 10px;
                    background-color: #f0f7ff;
                }
            """)
            self.count_label.setText(f"{len(self.attachments)} 张照片")
        else:
            self.setStyleSheet("""
                DropZone {
                    border: 2px dashed #9ca3af;
                    border-radius: 10px;
                    background-color: #fafafa;
                }
                DropZone:hover {
                    border-color: #4a90e2;
                    background-color: #f0f7ff;
                }
            """)
            self.count_label.setText("空")


class DraggableListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.IconMode)
        self.setIconSize(QSize(80, 80))
        self.setResizeMode(QListWidget.Adjust)
        self.setSpacing(8)
        self.setMovement(QListWidget.Free)
        self.setSpacing(6)
        self.setUniformItemSizes(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item:
            return

        data = item.data(Qt.UserRole)
        if not data:
            return

        attachment_id = data[0]
        file_path = data[1]

        mime_data = QMimeData()
        mime_data.setData('application/x-attachment-id', str(attachment_id).encode())
        mime_data.setText(f"attachment:{attachment_id}")

        drag = QDrag(self)
        drag.setMimeData(mime_data)

        pixmap = item.icon().pixmap(QSize(80, 80))
        if not pixmap.isNull():
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(40, 40))

        drag.exec(Qt.CopyAction | Qt.MoveAction)


class EditWindow(QWidget):
    record_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_record_id = None
        self.all_attachments = []
        self.section_drop_zones = {}
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setSizes([280, 900])

        left_panel = self.create_left_panel()
        right_panel = self.create_right_panel()

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

    def create_left_panel(self):
        panel = QFrame()
        panel.setStyleSheet("QFrame { background-color: #f9fafb; border-right: 1px solid #e5e7eb; }")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title_label = QLabel("待分配照片")
        title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #1f2937;")
        layout.addWidget(title_label)

        hint_label = QLabel("拖拽照片到右侧对应段落\n右键可预览或删除")
        hint_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(hint_label)

        self.attachment_list = DraggableListWidget()
        layout.addWidget(self.attachment_list, 1)

        self.empty_hint = QLabel("暂无待分配照片")
        self.empty_hint.setAlignment(Qt.AlignCenter)
        self.empty_hint.setStyleSheet("color: #9ca3af; font-size: 12px; padding: 20px;")
        self.empty_hint.hide()
        layout.addWidget(self.empty_hint)

        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d1d5db;
            }
        """)
        refresh_btn.clicked.connect(self.reload_all)
        btn_layout.addWidget(refresh_btn)
        layout.addLayout(btn_layout)

        return panel

    def create_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)

        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #eff6ff;
                border: 1px solid #bfdbfe;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        header_layout = QGridLayout(header_frame)
        header_layout.setSpacing(10)

        info_label = QLabel("📋 当前记录")
        info_label.setStyleSheet("font-weight: bold; color: #1e40af;")
        header_layout.addWidget(info_label, 0, 0, 1, 4)

        header_layout.addWidget(QLabel("工程:"), 1, 0)
        self.project_label = QLabel("-")
        self.project_label.setStyleSheet("font-weight: bold; color: #1f2937;")
        header_layout.addWidget(self.project_label, 1, 1)

        header_layout.addWidget(QLabel("楼栋:"), 1, 2)
        self.building_label = QLabel("-")
        self.building_label.setStyleSheet("font-weight: bold; color: #1f2937;")
        header_layout.addWidget(self.building_label, 1, 3)

        header_layout.addWidget(QLabel("日期:"), 2, 0)
        self.date_label = QLabel("-")
        header_layout.addWidget(self.date_label, 2, 1)

        header_layout.addWidget(QLabel("部位:"), 2, 2)
        self.location_label = QLabel("-")
        header_layout.addWidget(self.location_label, 2, 3)

        layout.addWidget(header_frame)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(12)
        scroll_layout.setContentsMargins(5, 5, 5, 5)

        basic_frame = self.create_basic_info_section()
        scroll_layout.addWidget(basic_frame)

        personnel_frame = self.create_section("personnel", "人员及设备情况")
        scroll_layout.addWidget(personnel_frame)

        inspection_frame = self.create_section("inspection", "检查情况")
        scroll_layout.addWidget(inspection_frame)

        handling_frame = self.create_section("handling", "处理意见")
        scroll_layout.addWidget(handling_frame)

        time_frame = self.create_time_section()
        scroll_layout.addWidget(time_frame)

        sign_frame = self.create_signature_section()
        scroll_layout.addWidget(sign_frame)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, 1)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("💾 保存记录")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #16a34a;
                color: white;
                padding: 12px 28px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #15803d;
            }
        """)
        save_btn.clicked.connect(self.save_record)

        clear_btn = QPushButton("重置模板")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6;
                color: #374151;
                padding: 10px 20px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
            }
        """)
        clear_btn.clicked.connect(self.reset_form)

        btn_layout.addStretch()
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        return panel

    def create_basic_info_section(self):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                padding: 15px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setSpacing(12)

        title = QLabel("一、基本信息")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #1f2937; border-bottom: 2px solid #e5e7eb; padding-bottom: 6px;")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(10)

        grid.addWidget(QLabel("施工单位:"), 0, 0)
        self.construction_unit_combo = QComboBox()
        self.construction_unit_combo.addItems(COMMON_CONSTRUCTION_UNITS)
        self.construction_unit_combo.setEditable(True)
        self.construction_unit_combo.setStyleSheet("QComboBox { padding: 6px; }")
        grid.addWidget(self.construction_unit_combo, 0, 1)

        grid.addWidget(QLabel("强度等级:"), 0, 2)
        self.strength_grade_combo = QComboBox()
        self.strength_grade_combo.addItems(STRENGTH_GRADES)
        self.strength_grade_combo.setStyleSheet("QComboBox { padding: 6px; }")
        grid.addWidget(self.strength_grade_combo, 0, 3)

        grid.addWidget(QLabel("配合比编号:"), 1, 0)
        self.mix_ratio_edit = QLineEdit()
        self.mix_ratio_edit.setPlaceholderText("例如：P2023-001")
        self.mix_ratio_edit.setStyleSheet("QLineEdit { padding: 6px; }")
        grid.addWidget(self.mix_ratio_edit, 1, 1)

        grid.addWidget(QLabel("天气:"), 1, 2)
        self.weather_combo = QComboBox()
        self.weather_combo.addItems(WEATHER_OPTIONS)
        self.weather_combo.setStyleSheet("QComboBox { padding: 6px; }")
        grid.addWidget(self.weather_combo, 1, 3)

        grid.addWidget(QLabel("气温:"), 2, 0)
        self.temperature_edit = QLineEdit()
        self.temperature_edit.setPlaceholderText("例如：25℃")
        self.temperature_edit.setStyleSheet("QLineEdit { padding: 6px; }")
        grid.addWidget(self.temperature_edit, 2, 1)

        grid.addWidget(QLabel("浇筑方量 (m³):"), 2, 2)
        self.volume_edit = QLineEdit()
        self.volume_edit.setStyleSheet("QLineEdit { padding: 6px; }")
        grid.addWidget(self.volume_edit, 2, 3)

        grid.addWidget(QLabel("罐车数量:"), 3, 0)
        self.truck_edit = QLineEdit()
        self.truck_edit.setStyleSheet("QLineEdit { padding: 6px; }")
        grid.addWidget(self.truck_edit, 3, 1)

        layout.addLayout(grid)

        self.basic_drop_zone = DropZone('basic_info', '基本信息')
        self.basic_drop_zone.set_edit_window(self)
        self.section_drop_zones['basic_info'] = self.basic_drop_zone
        layout.addWidget(self.basic_drop_zone)

        return frame

    def create_section(self, section_key, section_title):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        frame.setProperty("section_key", section_key)

        layout = QVBoxLayout(frame)
        layout.setSpacing(12)

        section_num = {'personnel': '二', 'inspection': '三', 'handling': '四'}
        num = section_num.get(section_key, '')

        title = QLabel(f"{num}、{section_title}")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #1f2937; border-bottom: 2px solid #e5e7eb; padding-bottom: 6px;")
        layout.addWidget(title)

        text_edit = QTextEdit()
        text_edit.setPlaceholderText(self.get_template_text(section_key))
        text_edit.setMinimumHeight(130)
        text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #fafafa;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
            }
        """)
        layout.addWidget(text_edit)

        setattr(self, f"{section_key}_edit", text_edit)

        drop_zone = DropZone(section_key, section_title)
        drop_zone.set_edit_window(self)
        self.section_drop_zones[section_key] = drop_zone
        layout.addWidget(drop_zone)

        return frame

    def create_time_section(self):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                padding: 15px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setSpacing(12)

        title = QLabel("五、浇筑时间")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #1f2937; border-bottom: 2px solid #e5e7eb; padding-bottom: 6px;")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(10)

        grid.addWidget(QLabel("开始时间:"), 0, 0)
        self.start_time_edit = QDateTimeEdit()
        self.start_time_edit.setCalendarPopup(True)
        self.start_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.start_time_edit.setDateTime(QDateTime.currentDateTime())
        self.start_time_edit.setStyleSheet("QDateTimeEdit { padding: 6px; }")
        grid.addWidget(self.start_time_edit, 0, 1)

        grid.addWidget(QLabel("结束时间:"), 0, 2)
        self.end_time_edit = QDateTimeEdit()
        self.end_time_edit.setCalendarPopup(True)
        self.end_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.end_time_edit.setDateTime(QDateTime.currentDateTime())
        self.end_time_edit.setStyleSheet("QDateTimeEdit { padding: 6px; }")
        grid.addWidget(self.end_time_edit, 0, 3)

        layout.addLayout(grid)

        return frame

    def create_signature_section(self):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                padding: 15px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setSpacing(12)

        title = QLabel("六、签字确认")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #1f2937; border-bottom: 2px solid #e5e7eb; padding-bottom: 6px;")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(10)

        grid.addWidget(QLabel("施工单位签字:"), 0, 0)
        self.constructor_signature_edit = QLineEdit()
        self.constructor_signature_edit.setPlaceholderText("请输入施工单位签字人姓名")
        self.constructor_signature_edit.setStyleSheet("QLineEdit { padding: 6px; }")
        grid.addWidget(self.constructor_signature_edit, 0, 1)

        grid.addWidget(QLabel("监理签字:"), 0, 2)
        self.supervisor_signature_edit = QLineEdit()
        self.supervisor_signature_edit.setPlaceholderText("请输入监理签字人姓名")
        self.supervisor_signature_edit.setStyleSheet("QLineEdit { padding: 6px; }")
        grid.addWidget(self.supervisor_signature_edit, 0, 3)

        layout.addLayout(grid)

        return frame

    def get_template_text(self, section_key):
        templates = {
            'personnel': '''施工单位现场管理人员：XXX（施工员）、XXX（质检员）
振捣班组：XXX等X人
浇筑班组：XXX等X人
主要设备：混凝土泵车X台、振捣棒X根、刮杠X套''',

            'inspection': '''1. 模板检查：模板支撑牢固，标高、轴线位置符合设计要求
2. 钢筋检查：钢筋规格、数量、间距符合设计要求，保护层厚度合格
3. 混凝土检查：坍落度实测XXXmm，符合配合比要求
4. 振捣情况：振捣密实，无漏振、过振现象
5. 现场试块：按要求留置标养试块X组、同条件试块X组''',

            'handling': '''1. 浇筑过程中发现XXX问题，已要求施工单位立即整改
2. 整改后经检查符合要求，同意继续浇筑
3. 已督促施工单位做好养护工作，养护时间不少于14天
4. 已按要求见证取样留置混凝土试块'''
        }
        return templates.get(section_key, '')

    def load_record(self, record_id):
        self.current_record_id = record_id
        record = db_manager.get_pouring_record_by_id(record_id)

        if not record:
            return

        projects = db_manager.get_all_projects()
        project_name = next((p['name'] for p in projects if p['id'] == record['project_id']), '-')
        buildings = db_manager.get_buildings_by_project(record['project_id'])
        building_name = next((b['name'] for b in buildings if b['id'] == record['building_id']), '-')

        self.project_label.setText(project_name)
        self.building_label.setText(building_name)
        self.date_label.setText(record['pouring_date'])
        self.location_label.setText(record['component_location'])

        idx = self.construction_unit_combo.findText(record['construction_unit'])
        if idx >= 0:
            self.construction_unit_combo.setCurrentIndex(idx)
        elif record['construction_unit']:
            self.construction_unit_combo.setEditText(record['construction_unit'])

        idx = self.strength_grade_combo.findText(record['strength_grade'])
        if idx >= 0:
            self.strength_grade_combo.setCurrentIndex(idx)

        self.mix_ratio_edit.setText(record['mix_ratio_no'])

        idx = self.weather_combo.findText(record['weather'])
        if idx >= 0:
            self.weather_combo.setCurrentIndex(idx)

        self.temperature_edit.setText(record['temperature'])
        self.volume_edit.setText(str(record['concrete_volume']) if record['concrete_volume'] else "")
        self.truck_edit.setText(str(record['truck_count']) if record['truck_count'] else "")

        self.personnel_edit.setPlainText(record['personnel_equipment'] or self.get_template_text('personnel'))
        self.inspection_edit.setPlainText(record['inspection_status'] or self.get_template_text('inspection'))
        self.handling_edit.setPlainText(record['handling_opinions'] or self.get_template_text('handling'))

        if record['start_time']:
            self.start_time_edit.setDateTime(QDateTime.fromString(record['start_time'], "yyyy-MM-dd HH:mm"))
        if record['end_time']:
            self.end_time_edit.setDateTime(QDateTime.fromString(record['end_time'], "yyyy-MM-dd HH:mm"))

        self.constructor_signature_edit.setText(record['constructor_signature'])
        self.supervisor_signature_edit.setText(record['supervisor_signature'])

        self.reload_all()

    def reload_all(self):
        self.reload_attachments()
        self.reload_section_images()

    def reload_attachments(self):
        self.attachment_list.clear()
        if not self.current_record_id:
            self.empty_hint.show()
            self.attachment_list.hide()
            return

        self.all_attachments = db_manager.get_attachments_by_record(self.current_record_id)

        unassigned = [a for a in self.all_attachments if a.get('file_type') == 'image' and not a.get('section_ref')]

        if not unassigned:
            self.empty_hint.show()
            self.attachment_list.hide()
            return

        self.empty_hint.hide()
        self.attachment_list.show()

        for att in unassigned:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, (att['id'], att['file_path']))

            if os.path.exists(att['file_path']):
                pixmap = QPixmap(att['file_path'])
                if not pixmap.isNull():
                    icon = QIcon(pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    item.setIcon(icon)

            item.setText(att['file_name'][:15])
            item.setSizeHint(QSize(100, 110))
            self.attachment_list.addItem(item)

    def reload_section_images(self):
        if not self.current_record_id:
            return

        self.all_attachments = db_manager.get_attachments_by_record(self.current_record_id)

        for section_key, drop_zone in self.section_drop_zones.items():
            drop_zone.clear_attachments()

            for att in self.all_attachments:
                if att.get('section_ref') == section_key:
                    drop_zone.add_attachment(att)

    def highlight_widget(self, widget):
        if not widget:
            return
        
        original_style = widget.styleSheet()
        
        highlight_style = """
            QFrame, QTextEdit, QLineEdit, QDateTimeEdit, QComboBox {
                background-color: #fef3c7 !important;
                border: 2px solid #f59e0b !important;
                border-radius: 8px;
            }
        """
        
        parent_frame = widget
        while parent_frame and not isinstance(parent_frame, QFrame):
            parent_frame = parent_frame.parentWidget()
        
        target = parent_frame if parent_frame else widget
        
        def apply_highlight():
            target.setStyleSheet(highlight_style)
        
        def restore():
            target.setStyleSheet(original_style)
        
        QTimer.singleShot(0, apply_highlight)
        
        for i, delay in enumerate([400, 800, 1200, 1600]):
            if i % 2 == 0:
                QTimer.singleShot(delay, restore)
            else:
                QTimer.singleShot(delay, apply_highlight)
        
        QTimer.singleShot(2000, restore)
    
    def focus_section(self, section_key):
        section_map = {
            'basic_info': (self.basic_drop_zone, '基本信息'),
            'personnel': (self.personnel_edit, '人员设备情况'),
            'inspection': (self.inspection_edit, '检查情况'),
            'handling': (self.handling_edit, '处理意见'),
            'time': (self.start_time_edit, '浇筑时间'),
            'signature': (self.constructor_signature_edit, '签字确认'),
        }
        
        result = section_map.get(section_key)
        if not result:
            return
        
        widget, section_name = result
        
        widget.setFocus()
        
        scroll_area = None
        parent = widget.parentWidget()
        while parent:
            if isinstance(parent, QScrollArea):
                scroll_area = parent
                break
            parent = parent.parentWidget()
        
        if scroll_area:
            QTimer.singleShot(50, lambda: scroll_area.ensureWidgetVisible(widget, 50, 200))
        
        QTimer.singleShot(100, lambda: self.highlight_widget(widget))

    def save_record(self):
        if not self.current_record_id:
            QMessageBox.warning(self, "提示", "请先选择一条浇筑记录")
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
            'construction_unit': self.construction_unit_combo.currentText().strip(),
            'strength_grade': self.strength_grade_combo.currentText(),
            'mix_ratio_no': self.mix_ratio_edit.text().strip(),
            'weather': self.weather_combo.currentText(),
            'temperature': self.temperature_edit.text().strip(),
            'personnel_equipment': self.personnel_edit.toPlainText().strip(),
            'inspection_status': self.inspection_edit.toPlainText().strip(),
            'handling_opinions': self.handling_edit.toPlainText().strip(),
            'concrete_volume': volume,
            'truck_count': truck_count,
            'start_time': self.start_time_edit.dateTime().toString("yyyy-MM-dd HH:mm"),
            'end_time': self.end_time_edit.dateTime().toString("yyyy-MM-dd HH:mm"),
            'supervisor_signature': self.supervisor_signature_edit.text().strip(),
            'constructor_signature': self.constructor_signature_edit.text().strip()
        }

        success = db_manager.update_pouring_record(self.current_record_id, record_data)

        if success:
            self.record_updated.emit()
            QMessageBox.information(self, "成功", "记录保存成功！")
        else:
            QMessageBox.warning(self, "失败", "保存失败，请重试")

    def reset_form(self):
        self.personnel_edit.setPlainText(self.get_template_text('personnel'))
        self.inspection_edit.setPlainText(self.get_template_text('inspection'))
        self.handling_edit.setPlainText(self.get_template_text('handling'))

    def on_record_selected(self, record_id):
        if record_id:
            self.load_record(record_id)
