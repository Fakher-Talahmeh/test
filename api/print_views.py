from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO

from .models import Exam, Schedule, Student, Hall, Instructor, InstructorOnHall


@api_view(['GET'])
@permission_classes([AllowAny])
def print_exam_schedule(request):
    """Generate PDF of exam schedule"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=1  # Center
    )
    
    # Title
    title = Paragraph('Exam Schedule', title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Get scheduled exams
    exams = Exam.objects.filter(date__isnull=False).order_by('date', 'time')
    
    # Create table data
    data = [['Exam Name', 'Course', 'Date', 'Time', 'Students', 'Halls']]
    
    for exam in exams:
        student_count = Schedule.objects.filter(examID=exam).count()
        halls = Hall.objects.filter(schedules__examID=exam).distinct()
        hall_names = ', '.join([hall.name for hall in halls])
        
        data.append([
            exam.name,
            exam.courseID.courseName,
            str(exam.date),
            str(exam.time),
            str(student_count),
            hall_names or 'Not assigned'
        ])
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="exam_schedule.pdf"'
    
    return response


@api_view(['GET'])
@permission_classes([AllowAny])
def print_student_schedule(request, studentID):
    """Generate PDF of student's exam schedule"""
    try:
        student = Student.objects.get(studentID=studentID)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found'}, status=404)
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    styles = getSampleStyleSheet()
    
    # Title
    title = Paragraph(f'Exam Schedule for {student.name}', styles['Heading1'])
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Get student's schedules
    schedules = Schedule.objects.filter(studentID=student).select_related('examID', 'hallID')
    
    # Create table data
    data = [['Exam', 'Course', 'Date', 'Time', 'Hall']]
    
    for schedule in schedules:
        exam = schedule.examID
        hall = schedule.hallID
        
        data.append([
            exam.name,
            exam.courseID.courseName,
            str(exam.date) if exam.date else 'TBD',
            str(exam.time) if exam.time else 'TBD',
            hall.name if hall else 'Not assigned'
        ])
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="student_{studentID}_schedule.pdf"'
    
    return response


@api_view(['GET'])
@permission_classes([AllowAny])
def print_hall_schedule(request, hallID):
    """Generate PDF of hall's exam schedule"""
    try:
        hall = Hall.objects.get(hallID=hallID)
    except Hall.DoesNotExist:
        return Response({'error': 'Hall not found'}, status=404)
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    styles = getSampleStyleSheet()
    
    # Title
    title = Paragraph(f'Exam Schedule for {hall.name}', styles['Heading1'])
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Get hall's schedules
    schedules = Schedule.objects.filter(hallID=hall).select_related('examID').values(
        'examID__name', 'examID__date', 'examID__time', 'examID'
    ).distinct()
    
    # Create table data
    data = [['Exam', 'Date', 'Time', 'Students', 'Instructors']]
    
    for schedule in schedules:
        exam_id = schedule['examID']
        student_count = Schedule.objects.filter(examID=exam_id, hallID=hall).count()
        
        instructors = Instructor.objects.filter(
            instructor_on_halls__examID=exam_id,
            instructor_on_halls__hallID=hall
        ).distinct()
        instructor_names = ', '.join([inst.name for inst in instructors])
        
        data.append([
            schedule['examID__name'],
            str(schedule['examID__date']) if schedule['examID__date'] else 'TBD',
            str(schedule['examID__time']) if schedule['examID__time'] else 'TBD',
            str(student_count),
            instructor_names or 'Not assigned'
        ])
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="hall_{hallID}_schedule.pdf"'
    
    return response
