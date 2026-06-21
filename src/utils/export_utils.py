import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


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


def check_record_issues(record, attachments, sign_records):
    issues = []
    
    if not record.get('supervisor_signature'):
        issues.append(('warning', '缺少监理签字'))
    
    if not record.get('constructor_signature'):
        issues.append(('warning', '缺少施工单位签字'))
    
    start_time = record.get('start_time', '')
    end_time = record.get('end_time', '')
    if start_time and end_time:
        try:
            start = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
            end = datetime.strptime(end_time, "%Y-%m-%d %H:%M")
            if end <= start:
                issues.append(('error', '结束时间早于或等于开始时间'))
        except:
            issues.append(('warning', '时间格式不正确'))
    
    pouring_date = record.get('pouring_date', '')
    if start_time and pouring_date:
        try:
            start = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
            p_date = datetime.strptime(pouring_date, "%Y-%m-%d")
            if start.date() != p_date.date():
                issues.append(('warning', '开始时间与浇筑日期不一致'))
        except:
            pass
    
    volume = record.get('concrete_volume', 0)
    truck_count = record.get('truck_count', 0)
    if truck_count > 0 and volume > 0:
        avg_volume = volume / truck_count
        if avg_volume < 5 or avg_volume > 15:
            issues.append(('warning', f'平均每车方量异常（{avg_volume:.1f}m³/车）'))
    
    image_attachments = [a for a in attachments if a.get('file_type') == 'image']
    if len(image_attachments) < 3:
        issues.append(('info', f'照片数量较少（{len(image_attachments)}张），建议补充关键节点照片'))
    
    has_ticket = any('小票' in a.get('file_name', '') or 'ticket' in a.get('file_name', '').lower() for a in attachments)
    if not has_ticket:
        issues.append(('info', '未检测到罐车小票附件'))
    
    has_delegation = any('委托' in a.get('file_name', '') or '试块' in a.get('file_name', '') for a in attachments)
    if not has_delegation:
        issues.append(('info', '未检测到试块委托单附件'))
    
    required_fields = ['construction_unit', 'strength_grade', 'mix_ratio_no', 'weather']
    for field in required_fields:
        if not record.get(field, ''):
            field_names = {
                'construction_unit': '施工单位',
                'strength_grade': '强度等级',
                'mix_ratio_no': '配合比编号',
                'weather': '天气'
            }
            issues.append(('warning', f'缺少必填项：{field_names[field]}'))
    
    return issues


def generate_pdf(record, attachments, sign_records, output_path):
    font_name = register_fonts()
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=10 * mm,
        textColor=colors.black
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName=font_name,
        fontSize=14,
        alignment=TA_LEFT,
        spaceBefore=5 * mm,
        spaceAfter=3 * mm,
        textColor=colors.black
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=11,
        alignment=TA_JUSTIFY,
        leading=18,
        textColor=colors.black
    )
    
    table_style = ParagraphStyle(
        'TableText',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        alignment=TA_LEFT,
        textColor=colors.black
    )
    
    story = []
    
    story.append(Paragraph('混凝土浇筑旁站监理记录', title_style))
    story.append(Spacer(1, 5 * mm))
    
    basic_data = [
        ['工程名称', record.get('project_name', ''), '楼栋号', record.get('building_name', '')],
        ['浇筑日期', record.get('pouring_date', ''), '构件部位', record.get('component_location', '')],
        ['施工单位', record.get('construction_unit', ''), '强度等级', record.get('strength_grade', '')],
        ['配合比编号', record.get('mix_ratio_no', ''), '天气情况', f"{record.get('weather', '')} {record.get('temperature', '')}"],
        ['浇筑方量', f"{record.get('concrete_volume', 0)} m³", '罐车数量', f"{record.get('truck_count', 0)} 车"],
        ['开始时间', record.get('start_time', ''), '结束时间', record.get('end_time', '')],
    ]
    
    basic_table = Table(basic_data, colWidths=[35 * mm, 55 * mm, 35 * mm, 55 * mm])
    basic_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('BACKGROUND', (2, 0), (2, -1), colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(basic_table)
    story.append(Spacer(1, 8 * mm))
    
    story.append(Paragraph('一、人员及设备情况', heading_style))
    story.append(Paragraph(record.get('personnel_equipment', '无') or '无', normal_style))
    story.append(Spacer(1, 3 * mm))
    
    section_attachments = {}
    for att in attachments:
        section_ref = att.get('section_ref', '')
        if section_ref:
            if section_ref not in section_attachments:
                section_attachments[section_ref] = []
            section_attachments[section_ref].append(att)
    
    if 'personnel' in section_attachments:
        story.extend(generate_image_section(section_attachments['personnel'], normal_style, table_style))
        story.append(Spacer(1, 3 * mm))
    
    story.append(Paragraph('二、检查情况', heading_style))
    story.append(Paragraph(record.get('inspection_status', '无') or '无', normal_style))
    story.append(Spacer(1, 3 * mm))
    
    if 'inspection' in section_attachments:
        story.extend(generate_image_section(section_attachments['inspection'], normal_style, table_style))
        story.append(Spacer(1, 3 * mm))
    
    story.append(Paragraph('三、处理意见', heading_style))
    story.append(Paragraph(record.get('handling_opinions', '无') or '无', normal_style))
    story.append(Spacer(1, 3 * mm))
    
    if 'handling' in section_attachments:
        story.extend(generate_image_section(section_attachments['handling'], normal_style, table_style))
        story.append(Spacer(1, 3 * mm))
    
    if 'basic_info' in section_attachments:
        story.append(Paragraph('四、相关资料照片', heading_style))
        story.extend(generate_image_section(section_attachments['basic_info'], normal_style, table_style))
        story.append(Spacer(1, 3 * mm))
    
    story.append(Spacer(1, 10 * mm))
    
    sign_data = [
        ['施工单位签字', '', '监理单位签字', ''],
        ['签字人：', record.get('constructor_signature', ''), '签字人：', record.get('supervisor_signature', '')],
        ['日期：', '', '日期：', ''],
    ]
    
    sign_table = Table(sign_data, colWidths=[35 * mm, 55 * mm, 35 * mm, 55 * mm])
    sign_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(sign_table)
    
    story.append(PageBreak())
    
    story.append(Paragraph('附件清单', title_style))
    story.append(Spacer(1, 5 * mm))
    
    if attachments:
        attachment_data = [['序号', '附件名称', '类型', '说明']]
        for idx, att in enumerate(attachments, 1):
            type_name = {'image': '照片', 'document': '文档', 'other': '其他'}.get(att.get('file_type', ''), '其他')
            attachment_data.append([
                str(idx),
                att.get('file_name', ''),
                type_name,
                att.get('description', '')
            ])
        
        attachment_table = Table(attachment_data, colWidths=[15 * mm, 60 * mm, 25 * mm, 80 * mm])
        attachment_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(attachment_table)
    
    other_images = [a for a in attachments if not a.get('section_ref', '') and a.get('file_type') == 'image']
    if other_images:
        story.append(Spacer(1, 10 * mm))
        story.append(Paragraph('其他照片资料', heading_style))
        story.extend(generate_image_section(other_images, normal_style, table_style))
    
    doc.build(story)
    return output_path


def generate_image_section(attachments, normal_style, table_style):
    elements = []
    image_attachments = [a for a in attachments if a.get('file_type') == 'image']
    
    if not image_attachments:
        return elements
    
    max_width = 170 * mm
    img_width = 55 * mm
    img_height = 40 * mm
    
    row_data = []
    for i, att in enumerate(image_attachments):
        img_path = att.get('file_path', '')
        if os.path.exists(img_path):
            try:
                img = Image(img_path, width=img_width, height=img_height, kind='proportional')
            except:
                img = Paragraph('[图片无法加载]', table_style)
        else:
            img = Paragraph('[图片文件不存在]', table_style)
        
        desc = att.get('description', '') or att.get('file_name', '')
        cell_content = [img, Spacer(1, 2 * mm), Paragraph(desc, table_style)]
        row_data.append(cell_content)
        
        if len(row_data) == 3 or i == len(image_attachments) - 1:
            while len(row_data) < 3:
                row_data.append('')
            
            table = Table([row_data], colWidths=[img_width + 5 * mm] * 3)
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
