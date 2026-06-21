import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
    PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from src.utils.file_utils import ATTACHMENT_CATEGORIES, get_category_info


def register_fonts():
    font_paths = [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
        r"/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        r"/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]

    for path in font_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont('CustomFont', path))
                return 'CustomFont'
            except:
                continue

    return 'Helvetica'


SECTION_LABELS = {
    'basic_info': '基本信息',
    'personnel': '人员及设备情况',
    'inspection': '检查情况',
    'handling': '处理意见',
    'time': '浇筑时间',
    'signature': '签字确认'
}


def check_record_issues(record, attachments, sign_records):
    issues = []

    if not record.get('supervisor_signature'):
        issues.append({
            'level': 'warning',
            'message': '缺少监理签字',
            'section': 'signature',
            'field': 'supervisor_signature',
            'suggestion': '请在『签字确认』区域填写监理人员姓名'
        })

    if not record.get('constructor_signature'):
        issues.append({
            'level': 'warning',
            'message': '缺少施工单位签字',
            'section': 'signature',
            'field': 'constructor_signature',
            'suggestion': '请在『签字确认』区域填写施工单位人员姓名'
        })

    start_time = record.get('start_time', '')
    end_time = record.get('end_time', '')
    if start_time and end_time:
        try:
            start = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
            end = datetime.strptime(end_time, "%Y-%m-%d %H:%M")
            if end <= start:
                issues.append({
                    'level': 'error',
                    'message': '结束时间早于或等于开始时间',
                    'section': 'time',
                    'field': 'end_time',
                    'suggestion': '请在『浇筑时间』区域调整开始或结束时间'
                })
        except:
            issues.append({
                'level': 'warning',
                'message': '时间格式不正确',
                'section': 'time',
                'field': 'start_time',
                'suggestion': '请确保时间格式为 YYYY-MM-DD HH:MM'
            })

    pouring_date = record.get('pouring_date', '')
    if start_time and pouring_date:
        try:
            start = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
            p_date = datetime.strptime(pouring_date, "%Y-%m-%d")
            if start.date() != p_date.date():
                issues.append({
                    'level': 'warning',
                    'message': '开始时间与浇筑日期不一致',
                    'section': 'time',
                    'field': 'start_time',
                    'suggestion': '请检查浇筑日期和开始时间是否匹配'
                })
        except:
            pass

    volume = record.get('concrete_volume', 0)
    truck_count = record.get('truck_count', 0)
    if truck_count > 0 and volume > 0:
        avg_volume = volume / truck_count
        if avg_volume < 5 or avg_volume > 15:
            issues.append({
                'level': 'warning',
                'message': f'平均每车方量异常（{avg_volume:.1f}m³/车）',
                'section': 'basic_info',
                'field': 'concrete_volume',
                'suggestion': '请在『基本信息』区域核对浇筑方量和罐车数量'
            })

    image_attachments = [a for a in attachments if a.get('file_type') == 'image']
    if len(image_attachments) < 3:
        issues.append({
            'level': 'info',
            'message': f'照片数量较少（{len(image_attachments)}张）',
            'section': None,
            'field': None,
            'suggestion': '建议补充关键节点照片（振捣、验收、试块留置等）'
        })

    has_ticket = any(a.get('category') == 'ticket' for a in attachments)
    if not has_ticket:
        issues.append({
            'level': 'info',
            'message': '未检测到罐车小票附件',
            'section': None,
            'field': None,
            'suggestion': '建议导入罐车送货小票或混凝土发货单'
        })

    has_delegation = any(a.get('category') == 'delegation' for a in attachments)
    if not has_delegation:
        issues.append({
            'level': 'info',
            'message': '未检测到试块委托单附件',
            'section': None,
            'field': None,
            'suggestion': '建议导入试块检测委托单或见证取样记录'
        })

    required_fields = [
        ('construction_unit', '施工单位', 'basic_info'),
        ('strength_grade', '强度等级', 'basic_info'),
        ('mix_ratio_no', '配合比编号', 'basic_info'),
        ('weather', '天气', 'basic_info')
    ]
    for field_key, field_name, section in required_fields:
        if not record.get(field_key, ''):
            issues.append({
                'level': 'warning',
                'message': f'缺少必填项：{field_name}',
                'section': section,
                'field': field_key,
                'suggestion': f'请在『{SECTION_LABELS.get(section, "基本信息")}』区域填写{field_name}'
            })

    personnel_content = record.get('personnel_equipment', '')
    if not personnel_content or len(personnel_content.strip()) < 10:
        issues.append({
            'level': 'info',
            'message': '人员设备情况内容较少',
            'section': 'personnel',
            'field': 'personnel_equipment',
            'suggestion': '建议详细填写施工管理人员、班组和设备信息'
        })

    inspection_content = record.get('inspection_status', '')
    if not inspection_content or len(inspection_content.strip()) < 10:
        issues.append({
            'level': 'warning',
            'message': '检查情况内容较少',
            'section': 'inspection',
            'field': 'inspection_status',
            'suggestion': '请详细填写模板、钢筋、混凝土、振捣等检查情况'
        })

    handling_content = record.get('handling_opinions', '')
    if not handling_content or len(handling_content.strip()) < 5:
        issues.append({
            'level': 'warning',
            'message': '处理意见内容较少',
            'section': 'handling',
            'field': 'handling_opinions',
            'suggestion': '请填写监理处理意见和整改要求'
        })

    priority = {'error': 0, 'warning': 1, 'info': 2}
    issues.sort(key=lambda x: priority.get(x['level'], 3))

    return issues


def generate_filename(record, projects, buildings):
    project_name = next((p['name'] for p in projects if p['id'] == record['project_id']), '')
    building_name = next((b['name'] for b in buildings if b['id'] == record['building_id']), '')

    def sanitize(text):
        return "".join(c for c in text if c.isalnum() or c in (' ', '-', '_', '号', '楼')).strip() or '未命名'

    safe_project = sanitize(project_name)
    safe_building = sanitize(building_name)
    safe_location = sanitize(record['component_location'])
    date_str = record['pouring_date']

    return f"旁站记录_{safe_project}_{safe_building}_{date_str}_{safe_location}.pdf"


def generate_pdf(record, attachments, sign_records, output_path):
    font_name = register_fonts()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=f"混凝土浇筑旁站监理记录 - {record.get('component_location', '')}",
        author="混凝土浇筑旁站资料整理工具"
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=6 * mm,
        textColor=colors.black,
        spaceBefore=0
    )

    doc_title_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=10 * mm,
        textColor=colors.grey
    )

    heading_style = ParagraphStyle(
        'SectionHead',
        parent=styles['Heading2'],
        fontName=font_name,
        fontSize=13,
        alignment=TA_LEFT,
        spaceBefore=6 * mm,
        spaceAfter=3 * mm,
        textColor=colors.black,
        borderWidth=0,
        leftIndent=0
    )

    normal_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=11,
        alignment=TA_JUSTIFY,
        leading=20,
        textColor=colors.black
    )

    table_text = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        alignment=TA_LEFT,
        textColor=colors.black,
        leading=16
    )

    caption_style = ParagraphStyle(
        'Caption',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.grey,
        leading=14
    )

    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        alignment=TA_LEFT,
        textColor=colors.HexColor('#1e40af'),
        backColor=colors.HexColor('#eff6ff'),
        borderPadding=(4, 8, 4, 8)
    )

    story = []

    story.append(Paragraph('混凝土浇筑旁站监理记录', title_style))
    story.append(Paragraph('Concrete Pouring Supervision Record', doc_title_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.grey, spaceBefore=0, spaceAfter=6 * mm))

    basic_data = [
        ['工程名称', record.get('project_name', ''), '楼栋号', record.get('building_name', '')],
        ['浇筑日期', record.get('pouring_date', ''), '构件部位', record.get('component_location', '')],
        ['施工单位', record.get('construction_unit', ''), '强度等级', record.get('strength_grade', '')],
        ['配合比编号', record.get('mix_ratio_no', ''), '天气情况', f"{record.get('weather', '')} {record.get('temperature', '')}".strip()],
        ['浇筑方量', f"{record.get('concrete_volume', 0)} m³", '罐车数量', f"{record.get('truck_count', 0)} 车"],
        ['开始时间', record.get('start_time', ''), '结束时间', record.get('end_time', '')],
    ]

    basic_table = Table(basic_data, colWidths=[35 * mm, 55 * mm, 35 * mm, 55 * mm])
    basic_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#f3f4f6')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(basic_table)
    story.append(Spacer(1, 8 * mm))

    section_attachments = {}
    for att in attachments:
        section_ref = att.get('section_ref', '')
        if section_ref:
            if section_ref not in section_attachments:
                section_attachments[section_ref] = []
            section_attachments[section_ref].append(att)

    sections = [
        ('personnel', '一、人员及设备情况', 'personnel_equipment'),
        ('inspection', '二、检查情况', 'inspection_status'),
        ('handling', '三、处理意见', 'handling_opinions')
    ]

    for sec_key, sec_title, field_key in sections:
        section_elements = []
        section_elements.append(Paragraph(sec_title, heading_style))
        section_elements.append(HRFlowable(width="40%", thickness=0.5, color=colors.HexColor('#3b82f6'), spaceAfter=3 * mm, hAlign='LEFT'))

        content = record.get(field_key, '')
        if content:
            for line in content.split('\n'):
                if line.strip():
                    section_elements.append(Paragraph(line.strip(), normal_style))
        else:
            section_elements.append(Paragraph('（未填写）', ParagraphStyle(
                'EmptyText', parent=normal_style, textColor=colors.grey
            )))

        if sec_key in section_attachments:
            section_elements.append(Spacer(1, 4 * mm))
            section_elements.append(Paragraph(f"📎 相关照片（{len(section_attachments[sec_key])}张）", section_header_style))
            section_elements.extend(generate_image_section(section_attachments[sec_key], normal_style, table_text, caption_style))

        story.append(KeepTogether(section_elements))
        story.append(Spacer(1, 2 * mm))

    if 'basic_info' in section_attachments:
        story.append(Paragraph('四、基本信息相关照片', heading_style))
        story.append(HRFlowable(width="40%", thickness=0.5, color=colors.HexColor('#3b82f6'), spaceAfter=3 * mm, hAlign='LEFT'))
        story.extend(generate_image_section(section_attachments['basic_info'], normal_style, table_text, caption_style))

    story.append(Spacer(1, 15 * mm))
    story.append(Paragraph('五、签字确认', heading_style))
    story.append(HRFlowable(width="40%", thickness=0.5, color=colors.HexColor('#3b82f6'), spaceAfter=6 * mm, hAlign='LEFT'))

    sign_data = [
        ['施工单位签字', '监理单位签字'],
        [
            Paragraph(f"<b>{record.get('constructor_signature', '') or '_______________'}</b>", ParagraphStyle('Sign', parent=table_text, fontSize=14, alignment=TA_CENTER)),
            Paragraph(f"<b>{record.get('supervisor_signature', '') or '_______________'}</b>", ParagraphStyle('Sign', parent=table_text, fontSize=14, alignment=TA_CENTER))
        ],
        ['日期：_______________', '日期：_______________'],
    ]

    sign_table = Table(sign_data, colWidths=[85 * mm, 85 * mm])
    sign_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(sign_table)

    story.append(PageBreak())

    story.append(Paragraph('附件清单', title_style))
    story.append(Paragraph('Appendix List', doc_title_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.grey, spaceBefore=0, spaceAfter=8 * mm))

    if attachments:
        grouped = {}
        for att in attachments:
            cat = att.get('category', 'other')
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(att)

        category_order = ['photo', 'ticket', 'delegation', 'draft', 'document', 'other']
        global_idx = 1

        for cat in category_order:
            if cat not in grouped:
                continue

            cat_info = get_category_info(cat)
            cat_items = grouped[cat]

            story.append(Paragraph(f"{cat_info['icon']} {cat_info['name']}（{len(cat_items)}项）", heading_style))
            story.append(Spacer(1, 2 * mm))

            table_rows = [['序号', '附件名称', '类型', '归属段落', '说明']]
            for att in cat_items:
                type_name = {'image': '照片', 'document': '文档', 'other': '其他'}.get(att.get('file_type', ''), '其他')
                section_ref = att.get('section_ref', '')
                section_name = SECTION_LABELS.get(section_ref, '未分配') if section_ref else '未分配'

                description = att.get('description', '') or att.get('file_name', '')
                if len(description) > 40:
                    description = description[:37] + '...'

                file_name = att.get('file_name', '')
                if len(file_name) > 30:
                    file_name = file_name[:27] + '...'

                table_rows.append([
                    str(global_idx),
                    file_name,
                    type_name,
                    section_name,
                    description
                ])
                global_idx += 1

            att_table = Table(table_rows, colWidths=[12 * mm, 50 * mm, 18 * mm, 25 * mm, 65 * mm])
            att_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e0e7ff')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(att_table)
            story.append(Spacer(1, 6 * mm))

        other_images = [a for a in attachments if not a.get('section_ref', '') and a.get('file_type') == 'image']
        if other_images:
            story.append(PageBreak())
            story.append(Paragraph('其他未分配照片资料', heading_style))
            story.append(Paragraph('（以下照片未分配到具体段落）', ParagraphStyle(
                'SubNote', parent=normal_style, fontSize=9, textColor=colors.grey, spaceAfter=4 * mm
            )))
            story.extend(generate_image_section(other_images, normal_style, table_text, caption_style))

    else:
        story.append(Paragraph('（无附件）', ParagraphStyle('EmptyNote', parent=normal_style, textColor=colors.grey, alignment=TA_CENTER)))

    doc.build(story)
    return output_path


def generate_image_section(attachments, normal_style, table_text, caption_style):
    elements = []
    image_attachments = [a for a in attachments if a.get('file_type') == 'image']

    if not image_attachments:
        return elements

    img_width = 53 * mm
    img_height = 40 * mm

    row_data = []
    for i, att in enumerate(image_attachments):
        img_path = att.get('file_path', '')
        if os.path.exists(img_path):
            try:
                img = Image(img_path, width=img_width, height=img_height, kind='proportional')
            except:
                img = Paragraph('[图片无法加载]', table_text)
        else:
            img = Paragraph('[图片文件不存在]', table_text)

        desc = att.get('description', '') or att.get('file_name', '')
        if len(desc) > 20:
            desc = desc[:17] + '...'

        cell_content = [
            img,
            Spacer(1, 2 * mm),
            Paragraph(desc, caption_style)
        ]
        row_data.append(cell_content)

        if len(row_data) == 3 or i == len(image_attachments) - 1:
            while len(row_data) < 3:
                row_data.append('')

            table = Table([row_data], colWidths=[img_width + 6 * mm] * 3)
            table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 3 * mm))
            row_data = []

    return elements
