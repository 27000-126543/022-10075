import sqlite3
import os
from pathlib import Path
from datetime import datetime


DB_PATH = os.path.join(str(Path.home()), ".concrete_log", "data.db")


def init_database():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS buildings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects (id),
        UNIQUE(project_id, name)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pouring_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        building_id INTEGER NOT NULL,
        pouring_date TEXT NOT NULL,
        component_location TEXT NOT NULL,
        construction_unit TEXT,
        strength_grade TEXT,
        mix_ratio_no TEXT,
        weather TEXT,
        temperature TEXT,
        personnel_equipment TEXT,
        inspection_status TEXT,
        handling_opinions TEXT,
        concrete_volume REAL,
        truck_count INTEGER,
        start_time TEXT,
        end_time TEXT,
        supervisor_signature TEXT,
        constructor_signature TEXT,
        exported_at TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects (id),
        FOREIGN KEY (building_id) REFERENCES buildings (id)
    )
    ''')
    
    cursor.execute("PRAGMA table_info(pouring_records)")
    record_columns = [col[1] for col in cursor.fetchall()]
    if 'exported_at' not in record_columns:
        cursor.execute("ALTER TABLE pouring_records ADD COLUMN exported_at TEXT")
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attachments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id INTEGER NOT NULL,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_type TEXT NOT NULL,
        file_size INTEGER,
        description TEXT,
        section_ref TEXT,
        category TEXT DEFAULT 'other',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (record_id) REFERENCES pouring_records (id)
    )
    ''')
    
    cursor.execute("PRAGMA table_info(attachments)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'category' not in columns:
        cursor.execute("ALTER TABLE attachments ADD COLUMN category TEXT DEFAULT 'other'")
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sign_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id INTEGER NOT NULL,
        signer_name TEXT NOT NULL,
        signer_role TEXT,
        sign_date TEXT,
        signature_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (record_id) REFERENCES pouring_records (id)
    )
    ''')
    
    conn.commit()
    conn.close()


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def add_project(name):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO projects (name) VALUES (?)", (name,))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        cursor.execute("SELECT id FROM projects WHERE name = ?", (name,))
        row = cursor.fetchone()
        return row['id'] if row else None
    finally:
        conn.close()


def add_building(project_id, name):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO buildings (project_id, name) VALUES (?, ?)", (project_id, name))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        cursor.execute("SELECT id FROM buildings WHERE project_id = ? AND name = ?", (project_id, name))
        row = cursor.fetchone()
        return row['id'] if row else None
    finally:
        conn.close()


def get_all_projects():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_buildings_by_project(project_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM buildings WHERE project_id = ? ORDER BY name", (project_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def add_pouring_record(record_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO pouring_records (
            project_id, building_id, pouring_date, component_location,
            construction_unit, strength_grade, mix_ratio_no, weather,
            temperature, personnel_equipment, inspection_status,
            handling_opinions, concrete_volume, truck_count,
            start_time, end_time, supervisor_signature, constructor_signature
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record_data.get('project_id'),
            record_data.get('building_id'),
            record_data.get('pouring_date'),
            record_data.get('component_location'),
            record_data.get('construction_unit', ''),
            record_data.get('strength_grade', ''),
            record_data.get('mix_ratio_no', ''),
            record_data.get('weather', ''),
            record_data.get('temperature', ''),
            record_data.get('personnel_equipment', ''),
            record_data.get('inspection_status', ''),
            record_data.get('handling_opinions', ''),
            record_data.get('concrete_volume', 0),
            record_data.get('truck_count', 0),
            record_data.get('start_time', ''),
            record_data.get('end_time', ''),
            record_data.get('supervisor_signature', ''),
            record_data.get('constructor_signature', '')
        ))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_pouring_record(record_id, record_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        existing = get_pouring_record_by_id(record_id)
        if not existing:
            return False
        
        fields = []
        values = []
        
        update_fields = [
            'construction_unit', 'strength_grade', 'mix_ratio_no',
            'weather', 'temperature', 'personnel_equipment',
            'inspection_status', 'handling_opinions', 'concrete_volume',
            'truck_count', 'start_time', 'end_time',
            'supervisor_signature', 'constructor_signature'
        ]
        
        defaults = {
            'construction_unit': '', 'strength_grade': '', 'mix_ratio_no': '',
            'weather': '', 'temperature': '', 'personnel_equipment': '',
            'inspection_status': '', 'handling_opinions': '',
            'concrete_volume': 0, 'truck_count': 0,
            'start_time': '', 'end_time': '',
            'supervisor_signature': '', 'constructor_signature': ''
        }
        
        for field in update_fields:
            if field in record_data:
                fields.append(f"{field} = ?")
                values.append(record_data[field])
            elif field in existing:
                fields.append(f"{field} = ?")
                values.append(existing[field])
            else:
                fields.append(f"{field} = ?")
                values.append(defaults[field])
        
        fields.append("updated_at = CURRENT_TIMESTAMP")
        
        query = f"UPDATE pouring_records SET {', '.join(fields)} WHERE id = ?"
        values.append(record_id)
        
        cursor.execute(query, values)
        conn.commit()
        return True
    finally:
        conn.close()


def get_pouring_records(project_id=None, building_id=None):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM pouring_records WHERE 1=1"
        params = []
        
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        if building_id:
            query += " AND building_id = ?"
            params.append(building_id)
        
        query += " ORDER BY pouring_date DESC, id DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_pouring_record_by_id(record_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pouring_records WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def add_attachment(attachment_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO attachments (record_id, file_name, file_path, file_type, file_size, description, section_ref, category)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            attachment_data.get('record_id'),
            attachment_data.get('file_name'),
            attachment_data.get('file_path'),
            attachment_data.get('file_type'),
            attachment_data.get('file_size', 0),
            attachment_data.get('description', ''),
            attachment_data.get('section_ref', ''),
            attachment_data.get('category', 'other')
        ))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_attachments_by_record(record_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM attachments WHERE record_id = ? ORDER BY created_at", (record_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def update_attachment_section(attachment_id, section_ref):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE attachments SET section_ref = ? WHERE id = ?", (section_ref, attachment_id))
        conn.commit()
        return True
    finally:
        conn.close()


def update_attachment_category(attachment_id, category):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE attachments SET category = ? WHERE id = ?", (category, attachment_id))
        conn.commit()
        return True
    finally:
        conn.close()


def update_attachment_description(attachment_id, description):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE attachments SET description = ? WHERE id = ?", (description, attachment_id))
        conn.commit()
        return True
    finally:
        conn.close()


def delete_attachment(attachment_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))
        conn.commit()
        return True
    finally:
        conn.close()


def add_sign_record(sign_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO sign_records (record_id, signer_name, signer_role, sign_date, signature_path)
        VALUES (?, ?, ?, ?, ?)
        ''', (
            sign_data.get('record_id'),
            sign_data.get('signer_name'),
            sign_data.get('signer_role', ''),
            sign_data.get('sign_date', ''),
            sign_data.get('signature_path', '')
        ))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_sign_records_by_record(record_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sign_records WHERE record_id = ? ORDER BY created_at", (record_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def update_record_exported(record_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE pouring_records SET exported_at = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (now, record_id))
        conn.commit()
        return True
    finally:
        conn.close()


def get_record_stats(record_id=None, project_id=None, building_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = """
            SELECT 
                pr.id,
                pr.project_id,
                pr.building_id,
                pr.pouring_date,
                pr.component_location,
                pr.construction_unit,
                pr.strength_grade,
                pr.concrete_volume,
                pr.supervisor_signature,
                pr.constructor_signature,
                pr.exported_at,
                SUM(CASE WHEN a.category = 'photo' THEN 1 ELSE 0 END) as photo_count,
                SUM(CASE WHEN a.category = 'ticket' THEN 1 ELSE 0 END) as ticket_count,
                SUM(CASE WHEN a.category = 'delegation' THEN 1 ELSE 0 END) as delegation_count,
                SUM(CASE WHEN a.category = 'draft' THEN 1 ELSE 0 END) as draft_count,
                SUM(CASE WHEN a.category = 'document' THEN 1 ELSE 0 END) as document_count,
                SUM(CASE WHEN a.category = 'other' THEN 1 ELSE 0 END) as other_count,
                COUNT(a.id) as total_attachments
            FROM pouring_records pr
            LEFT JOIN attachments a ON pr.id = a.record_id
            WHERE 1=1
        """
        params = []
        
        if record_id:
            query += " AND pr.id = ?"
            params.append(record_id)
        if project_id:
            query += " AND pr.project_id = ?"
            params.append(project_id)
        if building_id:
            query += " AND pr.building_id = ?"
            params.append(building_id)
        
        query += " GROUP BY pr.id ORDER BY pr.pouring_date DESC, pr.id DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def delete_pouring_record(record_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM attachments WHERE record_id = ?", (record_id,))
        cursor.execute("DELETE FROM sign_records WHERE record_id = ?", (record_id,))
        cursor.execute("DELETE FROM pouring_records WHERE id = ?", (record_id,))
        conn.commit()
        return True
    finally:
        conn.close()
