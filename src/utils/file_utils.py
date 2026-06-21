import os
import shutil
from pathlib import Path
from datetime import datetime
import hashlib


STORAGE_DIR = os.path.join(str(Path.home()), ".concrete_log", "attachments")

ATTACHMENT_CATEGORIES = {
    'photo': {
        'name': '现场照片',
        'icon': '📷',
        'keywords': ['照片', 'photo', 'image', 'img', '现场', '浇筑', '振捣', '模板', '钢筋', '试块', '验收']
    },
    'ticket': {
        'name': '罐车小票',
        'icon': '🧾',
        'keywords': ['小票', 'ticket', '送货', '发货', '罐车', '商混', '混凝土小票', '配合比单']
    },
    'delegation': {
        'name': '试块委托单',
        'icon': '📋',
        'keywords': ['委托', '试验', '检测', '送检', '试块', '报告', '见证取样']
    },
    'draft': {
        'name': '现场草稿',
        'icon': '📝',
        'keywords': ['草稿', '记录', '笔记', '手写', 'note', 'draft', '原始', '旁站记录']
    },
    'document': {
        'name': '其他文档',
        'icon': '📄',
        'keywords': []
    },
    'other': {
        'name': '其他文件',
        'icon': '📦',
        'keywords': []
    }
}


def ensure_storage_dir():
    os.makedirs(STORAGE_DIR, exist_ok=True)
    return STORAGE_DIR


def get_file_type(file_path):
    ext = Path(file_path).suffix.lower()
    image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic']
    doc_exts = ['.doc', '.docx', '.xls', '.xlsx', '.pdf', '.txt']
    
    if ext in image_exts:
        return 'image'
    elif ext in doc_exts:
        return 'document'
    else:
        return 'other'


def classify_attachment(file_path):
    file_name = os.path.basename(file_path).lower()
    file_type = get_file_type(file_path)
    
    if file_type == 'image':
        for cat_key in ['photo', 'ticket', 'delegation', 'draft']:
            cat = ATTACHMENT_CATEGORIES[cat_key]
            for keyword in cat['keywords']:
                if keyword.lower() in file_name:
                    return cat_key
        return 'photo'
    
    if file_type == 'document':
        for cat_key in ['ticket', 'delegation', 'draft']:
            cat = ATTACHMENT_CATEGORIES[cat_key]
            for keyword in cat['keywords']:
                if keyword.lower() in file_name:
                    return cat_key
        return 'document'
    
    return 'other'


def get_category_info(category_key):
    return ATTACHMENT_CATEGORIES.get(category_key, ATTACHMENT_CATEGORIES['other'])


def copy_to_storage(source_path, record_id, file_type=''):
    ensure_storage_dir()
    
    if not os.path.exists(source_path):
        return None
    
    record_dir = os.path.join(STORAGE_DIR, str(record_id))
    os.makedirs(record_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_name = Path(source_path).name
    name_stem = Path(source_path).stem
    extension = Path(source_path).suffix
    
    new_filename = f"{timestamp}_{name_stem}{extension}"
    dest_path = os.path.join(record_dir, new_filename)
    
    shutil.copy2(source_path, dest_path)
    
    return dest_path


def get_file_hash(file_path):
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def format_file_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def get_project_storage_dir(project_name):
    safe_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).strip()
    project_dir = os.path.join(STORAGE_DIR, safe_name)
    os.makedirs(project_dir, exist_ok=True)
    return project_dir
