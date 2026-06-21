from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class Project:
    id: Optional[int] = None
    name: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Building:
    id: Optional[int] = None
    project_id: int = 0
    name: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PouringRecord:
    id: Optional[int] = None
    project_id: int = 0
    building_id: int = 0
    pouring_date: str = ""
    component_location: str = ""
    construction_unit: str = ""
    strength_grade: str = ""
    mix_ratio_no: str = ""
    weather: str = ""
    temperature: str = ""
    personnel_equipment: str = ""
    inspection_status: str = ""
    handling_opinions: str = ""
    concrete_volume: float = 0.0
    truck_count: int = 0
    start_time: str = ""
    end_time: str = ""
    supervisor_signature: str = ""
    constructor_signature: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Attachment:
    id: Optional[int] = None
    record_id: int = 0
    file_name: str = ""
    file_path: str = ""
    file_type: str = ""
    file_size: int = 0
    description: str = ""
    section_ref: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SignRecord:
    id: Optional[int] = None
    record_id: int = 0
    signer_name: str = ""
    signer_role: str = ""
    sign_date: str = ""
    signature_path: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


SECTION_TEMPLATES = {
    'basic_info': {
        'name': '基本信息',
        'fields': ['construction_unit', 'strength_grade', 'mix_ratio_no', 'weather', 'temperature']
    },
    'personnel': {
        'name': '人员设备',
        'fields': ['personnel_equipment']
    },
    'inspection': {
        'name': '检查情况',
        'fields': ['inspection_status']
    },
    'handling': {
        'name': '处理意见',
        'fields': ['handling_opinions']
    }
}


WEATHER_OPTIONS = ['晴', '阴', '多云', '小雨', '中雨', '大雨', '雷阵雨', '雪', '雾']
STRENGTH_GRADES = ['C15', 'C20', 'C25', 'C30', 'C35', 'C40', 'C45', 'C50', 'C55', 'C60']
COMMON_CONSTRUCTION_UNITS = ['中国建筑', '中国中铁', '中国铁建', '中国交建', '中国电建', '上海建工', '北京城建', '其他']
