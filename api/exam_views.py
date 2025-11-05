from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.db.models import Count, Q
from datetime import datetime, timedelta
from dateutil import parser
import pytz

from .models import (
    Exam, Course, Student, Schedule, Hall, Instructor, InstructorOnHall,
    CourseMappings, CourseMappingRelation, AvailabilityDay, AvailabilityTime
)
from .serializers import ExamSerializer


@api_view(['PUT'])
@permission_classes([AllowAny])
def exam_update(request, id):
    """Update exam date/time and handle related schedules"""
    try:
        exam = Exam.objects.get(examID=id)
    except Exam.DoesNotExist:
        return Response({'message': 'No exam found with the given ID.'}, status=status.HTTP_404_NOT_FOUND)
    
    date_str = request.data.get('date')
    time_str = request.data.get('time')
    college = request.GET.get('college')
    
    if date_str is not None and time_str is not None:
        # Parse date string (format: "ddd, DD MMM")
        try:
            parsed_date = parser.parse(date_str)
            formatted_date = parsed_date.strftime('%Y-%m-%d')
        except:
            formatted_date = date_str
        
        # Update exam date and time
        exam.date = formatted_date
        exam.time = time_str
        exam.save()
        
        # Handle course mappings
        try:
            course = Course.objects.get(courseID=exam.courseID.courseID)
            course_mappings = course.course_mappings.all()
            
            for mapping in course_mappings:
                related_courses = mapping.courses.exclude(courseID=course.courseID)
                
                for related_course in related_courses:
                    try:
                        related_exam = Exam.objects.get(courseID=related_course)
                        related_exam.date = formatted_date
                        related_exam.time = time_str
                        related_exam.save()
                        
                        # Create schedules for related exam students
                        related_students = Student.objects.filter(courses=related_course)
                        for student in related_students:
                            Schedule.objects.get_or_create(
                                studentID=student,
                                examID=related_exam,
                                defaults={'college': college}
                            )
                    except Exam.DoesNotExist:
                        continue
        except Course.DoesNotExist:
            pass
        
        # Create schedules for original exam students
        original_students = Student.objects.filter(courses=exam.courseID)
        for student in original_students:
            Schedule.objects.get_or_create(
                studentID=student,
                examID=exam,
                defaults={'college': college}
            )
    else:
        # Reset exam (clear date, time, schedules)
        exam.date = None
        exam.time = None
        exam.save()
        
        InstructorOnHall.objects.filter(examID=exam).delete()
        Schedule.objects.filter(examID=exam).delete()
        
        # Handle course mappings
        try:
            course = Course.objects.get(courseID=exam.courseID.courseID)
            course_mappings = course.course_mappings.all()
            
            for mapping in course_mappings:
                related_courses = mapping.courses.exclude(courseID=course.courseID)
                
                for related_course in related_courses:
                    try:
                        related_exam = Exam.objects.get(courseID=related_course)
                        InstructorOnHall.objects.filter(examID=related_exam).delete()
                        Schedule.objects.filter(examID=related_exam).delete()
                        related_exam.date = None
                        related_exam.time = None
                        related_exam.save()
                    except Exam.DoesNotExist:
                        continue
        except Course.DoesNotExist:
            pass
    
    return Response({'message': 'Exam and equivalent exams updated successfully.'})


@api_view(['DELETE'])
@permission_classes([AllowAny])
def exam_delete(request, id):
    try:
        exam = Exam.objects.get(examID=id)
        exam.delete()
        return Response({'message': 'Exam deleted'})
    except Exam.DoesNotExist:
        return Response({'error': 'Exam not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def exam_select_hall(request, examID):
    """Assign halls to exam"""
    try:
        exam = Exam.objects.get(examID=examID)
    except Exam.DoesNotExist:
        return Response({'error': 'الامتحان غير موجود'}, status=status.HTTP_404_NOT_FOUND)
    
    selected_halls = request.data.get('selectedHalls', [])
    student_count = Schedule.objects.filter(examID=exam).count()
    
    for hall_data in selected_halls:
        hall_id = hall_data.get('hallID')
        try:
            hall = Hall.objects.get(hallID=hall_id)
        except Hall.DoesNotExist:
            continue
        
        hall_capacity = hall.capacity
        
        # Check if hall is already used at the same time
        existing_schedules = Schedule.objects.filter(
            hallID=hall,
            examID__date=exam.date,
            examID__time=exam.time
        ).exclude(examID=exam)
        
        hall_previously_used = existing_schedules.exists()
        
        if hall_previously_used:
            # Reduce capacity by existing usage
            existing_count = existing_schedules.count()
            hall_capacity = max(0, hall_capacity - existing_count)
        
        if student_count <= 0:
            break
        
        students_to_assign = min(student_count, hall_capacity)
        
        if students_to_assign > 0:
            # Assign students to hall
            unassigned_students = Schedule.objects.filter(
                examID=exam,
                hallID__isnull=True
            )[:students_to_assign]
            
            for schedule in unassigned_students:
                schedule.hallID = hall
                schedule.save()
            
            # If hall was previously used, copy instructors
            if hall_previously_used:
                existing_instructors = InstructorOnHall.objects.filter(
                    hallID=hall,
                    examID__date=exam.date,
                    examID__time=exam.time
                ).distinct()
                
                for inst_on_hall in existing_instructors:
                    InstructorOnHall.objects.get_or_create(
                        examID=exam,
                        hallID=hall,
                        instructorID=inst_on_hall.instructorID
                    )
            
            student_count -= students_to_assign
    
    return Response({'message': 'تم توزيع القاعات بنجاح'})


@api_view(['POST'])
@permission_classes([AllowAny])
def schedule_exams_auto(request):
    """Automatic exam scheduling algorithm"""
    try:
        exams = Exam.objects.filter(date__isnull=True).select_related('courseID')
        
        # Sort by number of enrolled students (descending)
        exam_student_counts = []
        for exam in exams:
            student_count = Student.objects.filter(courses=exam.courseID).count()
            exam_student_counts.append((exam, student_count))
        
        exam_student_counts.sort(key=lambda x: x[1], reverse=True)
        sorted_exams = [e[0] for e in exam_student_counts]
        
        # Generate time slots (14 working days, 2 time slots per day)
        time_slots = []
        start_date = datetime.now() + timedelta(days=1)
        days_assigned = 0
        
        while days_assigned < 14:
            # Skip Friday (4) and Saturday (5)
            if start_date.weekday() not in [4, 5]:
                time_slots.append({
                    'date': start_date.strftime('%Y-%m-%d'),
                    'exams': [],
                    'college_exam_count': {},
                    'student_exam_map': {},
                    'time_slots': {'09:00': [], '11:00': []}
                })
                days_assigned += 1
            start_date += timedelta(days=1)
        
        exam_schedule = {}
        
        # Assign exams to time slots
        for exam in sorted_exams:
            students = list(Student.objects.filter(courses=exam.courseID).values_list('studentID', flat=True))
            college = exam.college
            assigned = False
            
            for slot in time_slots:
                current_college_count = slot['college_exam_count'].get(college, 0)
                if current_college_count >= 3:
                    continue
                
                # Check for student conflicts
                conflict = any(s in slot['student_exam_map'] for s in students)
                if conflict:
                    continue
                
                # Determine time (09:00 or 11:00)
                time = '09:00'
                if len(slot['time_slots']['09:00']) > 0 and len(slot['time_slots']['11:00']) == 0:
                    time = '11:00'
                
                # If 11:00, check for high conflict with same college at 09:00
                if time == '11:00':
                    same_college_9am = [e for e in slot['time_slots']['09:00'] if e.college == college]
                    if same_college_9am:
                        # Check if any students overlap
                        high_conflict = False
                        for other_exam in same_college_9am:
                            other_students = set(Student.objects.filter(courses=other_exam.courseID).values_list('studentID', flat=True))
                            if set(students) & other_students:
                                high_conflict = True
                                break
                        if high_conflict:
                            continue
                
                # Assign exam
                slot['exams'].append(exam)
                slot['time_slots'][time].append(exam)
                slot['college_exam_count'][college] = current_college_count + 1
                exam_schedule[exam.examID] = {'date': slot['date'], 'time': time}
                
                for student_id in students:
                    slot['student_exam_map'][student_id] = True
                
                assigned = True
                break
        
        # Update exams in database
        for exam_id, schedule_info in exam_schedule.items():
            Exam.objects.filter(examID=exam_id).update(
                date=schedule_info['date'],
                time=schedule_info['time']
            )
        
        # Create schedules
        for exam in sorted_exams:
            if exam.examID in exam_schedule:
                students = Student.objects.filter(courses=exam.courseID)
                for student in students:
                    Schedule.objects.get_or_create(
                        studentID=student,
                        examID=exam,
                        defaults={'college': exam.college}
                    )
        
        return Response({
            'message': 'تم جدولة الامتحانات بنجاح مع تقليل التعارضات!',
            'schedule': exam_schedule
        })
    except Exception as error:
        return Response({'error': f'حدث خطأ أثناء الجدولة: {str(error)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def exam_schedules(request):
    """Get all scheduled exams"""
    exams = Exam.objects.filter(date__isnull=False).order_by('date', 'time')
    
    result = []
    for exam in exams:
        result.append({
            'name': exam.name,
            'date': str(exam.date),
            'time': str(exam.time)
        })
    
    return Response(result)


@api_view(['GET'])
@permission_classes([AllowAny])
def exam_hall_invigilators(request):
    """Get invigilators for exams at specific date and time"""
    date = request.GET.get('date')
    time = request.GET.get('time')
    
    exams = Exam.objects.filter(date=date, time=time)
    results = []
    
    for exam in exams:
        halls = Hall.objects.filter(instructor_on_halls__examID=exam).distinct()
        
        for hall in halls:
            instructors = Instructor.objects.filter(
                instructor_on_halls__examID=exam,
                instructor_on_halls__hallID=hall
            ).distinct()
            
            instructor_names = ' / '.join([inst.name for inst in instructors])
            
            results.append({
                'exam': exam.name,
                'hall': hall.name,
                'invigilators': instructor_names
            })
    
    return Response(results)
