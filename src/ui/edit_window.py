import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QTextEdit, QFrame, QSplitter, QListWidget, QListWidgetItem,
    QMessageBox, QScrollArea, QGridLayout, QDateTimeEdit,
    QAbstractItemView
)
from PySide6.QtCore import Qt, QDateTime, QMimeData, QSize
from PySide6.QtGui import (
    QDragEnterEvent, QDropEvent, QPixmap, QIcon
)

from src.database import db_manager
from src.models.models import STRENGTH_GRADES, WEATHER_OPTIONS, COMMON_CONSTRUCTION_UNITS


class DropZone(QFrame):
    def __init__(self, section_key, section_name, parent=None):
        super().__init__(parent)
        self.section_key = section_key
        self.section_name = section_name
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet("""
            DropZone {
                border: 2px dashed #bbb;
                border-radius: 8px;
                background-color: #fafafa;
                min-height: 80px;
            }
            DropZone:hover {
                border-color: #4a90e2;
                background-color: #f0f7ff;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        hint_label = QLabel(f"📎 拖拽照片到此处 - {section_name}")
        hint_label.setStyleSheet("color: #888; font-size: 12px;")
        hint_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint_label)
        
        self.images_layout = QHBoxLayout()
        self.images_layout.setSpacing(5)
        layout.addLayout(self.images_layout)
        
        self.attachments = []
        self.edit_window = None
    
    def set_edit_window(self, window):
        self.edit_window = window
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasFormat('application/x-attachment-id'):
            event.acceptProposedAction()
    
    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat('application/x-attachment-id'):
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        attachment_id = int(event.mimeData().data('application/x-attachment-id').data().decode())
        
        db_manager.update_attachment_section(attachment_id, self.section_key)
        
        if self.edit_window:
            self.edit_window.reload_attachments()
            self.edit_window.reload_section_images()
    
    def add_attachment(self, attachment):
        self.attachments.append(attachment)
        self.update_display()
    
    def clear_attachments(self):
        self.attachments = []
        self.update_display()
    
    def update_display(self):
        while self.images_layout.count():
            child = self.images_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        for att in self.attachments:
            if att.get('file_type') == 'image' and os.path.exists(att['file_path']):
                img_label = QLabel()
                pixmap = QPixmap(att['file_path'])
                if not pixmap.isNull():
                    scaled = pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    img_label.setPixmap(scaled)
                    img_label.setToolTip(att['file_name'])
                    img_label.setStyleSheet("""
                        QLabel {
                            border: 1px solid #ccc;
                            border-radius: 4px;
                            padding: 2px;
                            background-color: white;
                        }
                    """)
                    img_label.setCursor(Qt.PointingHandCursor)
                    img_label.mouseDoubleClickEvent = lambda e, path=att['file_path']: os.startfile(path)
                    self.images_layout.addWidget(img_label)
        
        if not self.attachments:
            self.setStyleSheet("""
                DropZone {
                    border: 2px dashed #bbb;
                    border-radius: 8px;
                    background-color: #fafafa;
                    min-height: 80px;
                }
                DropZone:hover {
                    border-color: #4a90e2;
                    background-color: #f0f7ff;
                }
            """)
        else:
            self.setStyleSheet("""
                DropZone {
                    border: 2px solid #4a90e2;
                    border-radius: 8px;
                    background-color: #f0f7ff;
                    min-height: 80px;
                }
            """)


class DraggableListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragOnly)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setIconSize(QSize(64, 64))
    
    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item:
            return
        
        data = item.data(Qt.UserRole)
        if not data:
            return
        
        attachment_id = data[0]
        
        mime_data = QMimeData()
        mime_data.setData('application/x-attachment-id', str(attachment_id).encode())
        
        pixmap = item.icon().pixmap(QSize(64, 64))
        
        drag = self.startDrag(supportedActions)
        drag.setMimeData(mime_data)
        if not pixmap.isNull():
            drag.setPixmap(pixmap)
        drag.exec(Qt.CopyAction)


class EditWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_record_id = None
        self.all_attachments = []
        self.section_drop_zones = {}
        self.init_ui()
    
    def init_ui(self):
        main_layout = QHBoxLayout(self)
        
        splitter = QSplitter(Qt.Horizontal)
        
        left_panel = self.create_left_panel()
        right_panel = self.create_right_panel()
        
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        main_layout.addWidget(splitter)
    
    def create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        title_label = QLabel("待分配照片")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title_label)
        
        hint_label = QLabel("拖拽照片到右侧对应段落")
        hint_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(hint_label)
        
        self.attachment_list = DraggableListWidget()
        self.attachment_list.setIconSize(QSize(64, 64))
        layout.addWidget(self.attachment_list, 1)
        
        refresh_btn = QPushButton("🔄 刷新附件列表")
        refresh_btn.clicked.connect(self.reload_attachments)
        layout.addWidget(refresh_btn)
        
        return panel
    
    def create_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel)
        header_layout = QGridLayout(header_frame)
        
        header_layout.addWidget(QLabel("工程名称:"), 0, 0)
        self.project_label = QLabel("-")
        self.project_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(self.project_label, 0, 1)
        
        header_layout.addWidget(QLabel("楼栋:"), 0, 2)
        self.building_label = QLabel("-")
        self.building_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(self.building_label, 0, 3)
        
        header_layout.addWidget(QLabel("浇筑日期:"), 1, 0)
        self.date_label = QLabel("-")
        header_layout.addWidget(self.date_label, 1, 1)
        
        header_layout.addWidget(QLabel("构件部位:"), 1, 2)
        self.location_label = QLabel("-")
        header_layout.addWidget(self.location_label, 1, 3)
        
        layout.addWidget(header_frame)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)
        
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
                background-color: #27ae60;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        save_btn.clicked.connect(self.save_record)
        
        clear_btn = QPushButton("重置表单")
        clear_btn.clicked.connect(self.reset_form)
        
        btn_layout.addStretch()
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
        
        return panel
    
    def create_basic_info_section(self):
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        
        title = QLabel("一、基本信息")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)
        
        grid = QGridLayout()
        grid.setSpacing(10)
        
        grid.addWidget(QLabel("施工单位:"), 0, 0)
        self.construction_unit_combo = QComboBox()
        self.construction_unit_combo.addItems(COMMON_CONSTRUCTION_UNITS)
        self.construction_unit_combo.setEditable(True)
        grid.addWidget(self.construction_unit_combo, 0, 1)
        
        grid.addWidget(QLabel("强度等级:"), 0, 2)
        self.strength_grade_combo = QComboBox()
        self.strength_grade_combo.addItems(STRENGTH_GRADES)
        grid.addWidget(self.strength_grade_combo, 0, 3)
        
        grid.addWidget(QLabel("配合比编号:"), 1, 0)
        self.mix_ratio_edit = QLineEdit()
        self.mix_ratio_edit.setPlaceholderText("例如：P2023-001")
        grid.addWidget(self.mix_ratio_edit, 1, 1)
        
        grid.addWidget(QLabel("天气:"), 1, 2)
        self.weather_combo = QComboBox()
        self.weather_combo.addItems(WEATHER_OPTIONS)
        grid.addWidget(self.weather_combo, 1, 3)
        
        grid.addWidget(QLabel("气温:"), 2, 0)
        self.temperature_edit = QLineEdit()
        self.temperature_edit.setPlaceholderText("例如：25℃")
        grid.addWidget(self.temperature_edit, 2, 1)
        
        grid.addWidget(QLabel("浇筑方量 (m³):"), 2, 2)
        self.volume_edit = QLineEdit()
        grid.addWidget(self.volume_edit, 2, 3)
        
        grid.addWidget(QLabel("罐车数量:"), 3, 0)
        self.truck_edit = QLineEdit()
        grid.addWidget(self.truck_edit, 3, 1)
        
        layout.addLayout(grid)
        
        self.basic_drop_zone = DropZone('basic_info', '基本信息')
        self.basic_drop_zone.set_edit_window(self)
        self.section_drop_zones['basic_info'] = self.basic_drop_zone
        layout.addWidget(self.basic_drop_zone)
        
        return frame
    
    def create_section(self, section_key, section_title):
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        
        section_num = {'personnel': '二', 'inspection': '三', 'handling': '四'}
        num = section_num.get(section_key, '')
        
        title = QLabel(f"{num}、{section_title}")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)
        
        text_edit = QTextEdit()
        text_edit.setPlaceholderText(self.get_template_text(section_key))
        text_edit.setMinimumHeight(120)
        text_edit.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
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
        frame.setFrameStyle(QFrame.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        
        title = QLabel("五、浇筑时间")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)
        
        grid = QGridLayout()
        
        grid.addWidget(QLabel("开始时间:"), 0, 0)
        self.start_time_edit = QDateTimeEdit()
        self.start_time_edit.setCalendarPopup(True)
        self.start_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.start_time_edit.setDateTime(QDateTime.currentDateTime())
        grid.addWidget(self.start_time_edit, 0, 1)
        
        grid.addWidget(QLabel("结束时间:"), 0, 2)
        self.end_time_edit = QDateTimeEdit()
        self.end_time_edit.setCalendarPopup(True)
        self.end_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.end_time_edit.setDateTime(QDateTime.currentDateTime())
        grid.addWidget(self.end_time_edit, 0, 3)
        
        layout.addLayout(grid)
        
        return frame
    
    def create_signature_section(self):
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        
        title = QLabel("六、签字确认")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)
        
        grid = QGridLayout()
        
        grid.addWidget(QLabel("施工单位签字:"), 0, 0)
        self.constructor_signature_edit = QLineEdit()
        self.constructor_signature_edit.setPlaceholderText("请输入施工单位签字人姓名")
        grid.addWidget(self.constructor_signature_edit, 0, 1)
        
        grid.addWidget(QLabel("监理签字:"), 0, 2)
        self.supervisor_signature_edit = QLineEdit()
        self.supervisor_signature_edit.setPlaceholderText("请输入监理签字人姓名")
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
        else:
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
        
        self.reload_attachments()
        self.reload_section_images()
    
    def reload_attachments(self):
        self.attachment_list.clear()
        if not self.current_record_id:
            return
        
        self.all_attachments = db_manager.get_attachments_by_record(self.current_record_id)
        
        for att in self.all_attachments:
            if att.get('file_type') == 'image' and not att.get('section_ref'):
                item = QListWidgetItem()
                item.setData(Qt.UserRole, (att['id'], att['file_path']))
                
                if os.path.exists(att['file_path']):
                    pixmap = QPixmap(att['file_path'])
                    if not pixmap.isNull():
                        icon = QIcon(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                        item.setIcon(icon)
                
                item.setText(f"📷 {att['file_name']}")
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
