import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database import db_manager
from src.utils import file_utils, export_utils


def test_database():
    print("=" * 50)
    print("测试数据库功能...")
    print("=" * 50)
    
    db_manager.init_database()
    
    project_id = db_manager.add_project("测试项目")
    print(f"✓ 创建项目: 测试项目 (ID: {project_id})")
    
    building_id = db_manager.add_building(project_id, "1#楼")
    print(f"✓ 创建楼栋: 1#楼 (ID: {building_id})")
    
    record_data = {
        'project_id': project_id,
        'building_id': building_id,
        'pouring_date': '2024-01-15',
        'component_location': '地下室负一层墙柱',
        'construction_unit': '中国建筑',
        'strength_grade': 'C30',
        'mix_ratio_no': 'P2024-001',
        'weather': '晴',
        'temperature': '25℃',
        'concrete_volume': 120.5,
        'truck_count': 12,
        'start_time': '2024-01-15 08:00',
        'end_time': '2024-01-15 18:00',
        'supervisor_signature': '张监理',
        'constructor_signature': '李施工'
    }
    
    record_id = db_manager.add_pouring_record(record_data)
    print(f"✓ 创建浇筑记录 (ID: {record_id})")
    
    projects = db_manager.get_all_projects()
    print(f"✓ 查询项目列表: {len(projects)} 个项目")
    
    buildings = db_manager.get_buildings_by_project(project_id)
    print(f"✓ 查询楼栋列表: {len(buildings)} 个楼栋")
    
    records = db_manager.get_pouring_records(project_id, building_id)
    print(f"✓ 查询浇筑记录列表: {len(records)} 条记录")
    
    record = db_manager.get_pouring_record_by_id(record_id)
    print(f"✓ 查询单条记录: {record['component_location']}")
    
    update_data = {
        'construction_unit': '中国建筑第八工程局',
        'handling_opinions': '浇筑过程正常，同意验收'
    }
    db_manager.update_pouring_record(record_id, update_data)
    print("✓ 更新浇筑记录")
    
    return project_id, building_id, record_id


def test_file_utils():
    print("\n" + "=" * 50)
    print("测试文件工具功能...")
    print("=" * 50)
    
    storage_dir = file_utils.ensure_storage_dir()
    print(f"✓ 存储目录: {storage_dir}")
    print(f"✓ 目录存在: {os.path.exists(storage_dir)}")
    
    test_file = __file__
    file_type = file_utils.get_file_type(test_file)
    print(f"✓ 文件类型检测: {test_file} -> {file_type}")
    
    test_image = "test.jpg"
    file_type = file_utils.get_file_type(test_image)
    print(f"✓ 图片类型检测: {test_image} -> {file_type}")
    
    test_doc = "test.docx"
    file_type = file_utils.get_file_type(test_doc)
    print(f"✓ 文档类型检测: {test_doc} -> {file_type}")
    
    size_str = file_utils.format_file_size(1024)
    print(f"✓ 文件大小格式化: 1024 bytes -> {size_str}")
    
    size_str = file_utils.format_file_size(1024 * 1024)
    print(f"✓ 文件大小格式化: 1MB -> {size_str}")


def test_export_utils(record_id):
    print("\n" + "=" * 50)
    print("测试导出检查功能...")
    print("=" * 50)
    
    record = db_manager.get_pouring_record_by_id(record_id)
    attachments = db_manager.get_attachments_by_record(record_id)
    sign_records = db_manager.get_sign_records_by_record(record_id)
    
    issues = export_utils.check_record_issues(record, attachments, sign_records)
    
    if issues:
        print(f"✓ 检测到 {len(issues)} 个问题:")
        for issue in issues:
            level = issue.get('level', 'info')
            message = issue.get('message', '')
            section = issue.get('section', '')
            icon = {'error': '❌', 'warning': '⚠️', 'info': 'ℹ️'}.get(level, '•')
            section_text = f" [{section}]" if section else ""
            print(f"  {icon} {message}{section_text}")
    else:
        print("✓ 未检测到问题")
    
    error_count = sum(1 for i in issues if i.get('level') == 'error')
    warning_count = sum(1 for i in issues if i.get('level') == 'warning')
    info_count = sum(1 for i in issues if i.get('level') == 'info')
    print(f"✓ 问题统计: {error_count}个错误, {warning_count}个警告, {info_count}个提示")
    
    print("\n✓ 附件分类功能测试...")
    test_files = [
        '现场照片_浇筑.jpg',
        '罐车小票_20240115.pdf',
        '试块委托单.xlsx',
        '旁站记录草稿.txt',
        '普通文档.docx'
    ]
    for f in test_files:
        cat = file_utils.classify_attachment(f)
        cat_info = file_utils.get_category_info(cat)
        print(f"  {cat_info['icon']} {f} -> {cat_info['name']}")
    
    print("\n✓ 文件名生成测试...")
    projects = db_manager.get_all_projects()
    buildings = db_manager.get_buildings_by_project(record['project_id'])
    filename = export_utils.generate_filename(record, projects, buildings)
    print(f"  生成文件名: {filename}")
    
    print("\n✓ 中文字体注册测试...")
    font_name = export_utils.register_fonts()
    print(f"  使用字体: {font_name}")


def test_cleanup(record_id):
    print("\n" + "=" * 50)
    print("清理测试数据...")
    print("=" * 50)
    
    db_manager.delete_pouring_record(record_id)
    print(f"✓ 删除浇筑记录 (ID: {record_id})")


def main():
    print("\n" + "🚀 混凝土浇筑旁站资料整理工具 - 核心功能测试\n")
    
    try:
        project_id, building_id, record_id = test_database()
        test_file_utils()
        test_export_utils(record_id)
        test_cleanup(record_id)
        
        print("\n" + "=" * 50)
        print("✅ 所有测试通过！")
        print("=" * 50)
        print("\n可以运行 'python main.py' 启动完整的GUI程序。")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
