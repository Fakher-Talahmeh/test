from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.db.models import Count
from dateutil import parser
from datetime import datetime

from .models import (
    Instructor, AvailabilityDay, AvailabilityTime, Exam, Hall, Schedule,
    InstructorOnHall, Course
)


@api_view(['GET'])
@permission_classes([AllowAny])
def selection_halls(request):
    """Get halls with their scheduled exams and instructors"""
    halls = Hall.objects.prefetch_related('schedules__examID').all()
    
    selection = []
    seen = set()
    
    for hall in halls:
        schedules = hall.schedules.all()
        
        if schedules.exists():
            for schedule in schedules:
                exam = schedule.examID
                if not exam:
                    continue
                
                unique_key = f"{hall.hallID}-{exam.examID}"
                
                if unique_key not in seen:
                    count = Schedule.objects.filter(examID=exam, hallID=hall).count()
                    
                    instructors = Instructor.objects.filter(
                        instructor_on_halls__hallID=hall,
                        instructor_on_halls__examID=exam
                    ).distinct()
                    
                    instructor_names = ' / '.join([inst.name for inst in instructors]) if instructors.exists() else ''
                    
                    selection.append({
                        'examID': exam.examID,
                        'hall': hall.name,
                        'name': exam.name,
                        'NUM': count,
                        'date': str(exam.date) if exam.date else None,
                        'time': str(exam.time) if exam.time else None,
                        'invigilators': instructor_names
                    })
                    
                    seen.add(unique_key)
    
    return Response(selection)


@api_view(['GET'])
@permission_classes([AllowAny])
def invigilator_exist(request, examID):
    """Get available instructors for a specific exam"""
    try:
        exam = Exam.objects.select_related('courseID').get(examID=examID)
    except Exam.DoesNotExist:
        return Response({'error': 'الامتحان غير موجود أو لا يحتوي على تاريخ أو وقت'}, status=status.HTTP_404_NOT_FOUND)
    
    if not exam.date or not exam.time:
        return Response({'error': 'الامتحان غير موجود أو لا يحتوي على تاريخ أو وقت'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get all instructors with their availability
    instructors = Instructor.objects.prefetch_related(
        'availability_days__availability_slots'
    ).all()
    
    # Filter instructors available at exam date and time
    available_instructors = []
    
    for instructor in instructors:
        is_available = False
        
        for availability_day in instructor.availability_days.all():
            # Parse availability date (format: "01Jan", "15Feb", etc.)
            try:
                # Extract day and month from format like "01Jan"
                day_str = availability_day.date[:2]
                month_str = availability_day.date[2:]
                
                # Create a date string and compare
                date_str = f"2024-{month_str}-{day_str}"
                availability_date = parser.parse(date_str)
                
                # Check if dates match (day and month)
                if availability_date.day == exam.date.day and availability_date.month == exam.date.month:
                    # Check time slots
                    for time_slot in availability_day.availability_slots.all():
                        # Parse time (format: "9:00AM", "11:00AM")
                        try:
                            slot_time = parser.parse(time_slot.time)
                            exam_time = datetime.strptime(str(exam.time), '%H:%M:%S')
                            
                            if slot_time.hour == exam_time.hour and slot_time.minute == exam_time.minute:
                                is_available = True
                                break
                        except:
                            continue
                
                if is_available:
                    break
            except:
                continue
        
        if is_available:
            available_instructors.append(instructor)
    
    # Filter out instructors already assigned to overlapping exams
    overlapping_exams = Exam.objects.filter(date=exam.date, time=exam.time).exclude(examID=exam.examID)
    
    my_exam_instructors = InstructorOnHall.objects.filter(examID=exam).values_list('instructorID', flat=True)
    
    final_available_instructors = []
    for instructor in available_instructors:
        is_assigned_elsewhere = InstructorOnHall.objects.filter(
            instructorID=instructor,
            examID__in=overlapping_exams
        ).exclude(instructorID__in=my_exam_instructors).exists()
        
        if not is_assigned_elsewhere:
            final_available_instructors.append({
                'instructorID': instructor.instructorID,
                'name': instructor.name,
                'email': instructor.email
            })
    
    return Response(final_available_instructors)


@api_view(['POST'])
@permission_classes([AllowAny])
def select_instructor(request, hall, examID):
    """Assign instructors to a hall for an exam"""
    try:
        hall_obj = Hall.objects.get(name=hall)
        exam = Exam.objects.get(examID=examID)
    except (Hall.DoesNotExist, Exam.DoesNotExist):
        return Response({'error': 'Hall or Exam not found'}, status=status.HTTP_404_NOT_FOUND)
    
    selected_invigilators = request.data.get('selectedInvigilators', [])
    
    for invigilator_data in selected_invigilators:
        instructor_id = invigilator_data.get('instructorID')
        
        try:
            instructor = Instructor.objects.get(instructorID=instructor_id)
            
            # Create instructor assignment
            InstructorOnHall.objects.get_or_create(
                examID=exam,
                hallID=hall_obj,
                instructorID=instructor
            )
            
            # Assign to other exams at same date/time using the same hall
            same_time_exams = Exam.objects.filter(date=exam.date, time=exam.time).exclude(examID=exam.examID)
            
            for other_exam in same_time_exams:
                # Check if this hall is used for the other exam
                if Schedule.objects.filter(examID=other_exam, hallID=hall_obj).exists():
                    InstructorOnHall.objects.get_or_create(
                        examID=other_exam,
                        hallID=hall_obj,
                        instructorID=instructor
                    )
        except Instructor.DoesNotExist:
            continue
    
    return Response({'message': 'Update of Instructor on hall'})


@api_view(['POST'])
@permission_classes([AllowAny])
def instructors_for_exam_and_hall_delete(request):
    """Remove instructor assignment from exam and hall"""
    exam_id = request.data.get('examID')
    hall_id = request.data.get('hallID')
    instructor_id = request.data.get('instructorID')
    
    InstructorOnHall.objects.filter(
        examID=exam_id,
        hallID=hall_id,
        instructorID=instructor_id
    ).delete()
    
    return Response({'message': 'remove the instructor.'})


@api_view(['GET'])
@permission_classes([AllowAny])
def instructors_for_exam_and_hall(request, examID, hallID):
    """Get instructors assigned to a specific exam and hall"""
    try:
        exam = Exam.objects.get(examID=examID)
        hall = Hall.objects.get(hallID=hallID)
    except (Exam.DoesNotExist, Hall.DoesNotExist):
        return Response({'message': 'Exam or Hall not found'}, status=status.HTTP_404_NOT_FOUND)
    
    instructors = Instructor.objects.filter(
        instructor_on_halls__examID=exam,
        instructor_on_halls__hallID=hall
    ).distinct()
    
    if not instructors.exists():
        return Response({
            'message': 'No instructors found for the specified exam and hall'
        }, status=status.HTTP_404_NOT_FOUND)
    
    result = []
    for instructor in instructors:
        result.append({
            'instructorID': instructor.instructorID,
            'name': instructor.name,
            'email': instructor.email
        })
    
    return Response(result)
