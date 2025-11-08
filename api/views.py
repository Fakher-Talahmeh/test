from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action, permission_classes,authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Q, Count, F
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
import jwt
from django.conf import settings

from .models import (
    Adminn as Admin, Student, Course, Enrollment, CourseMappings, CourseMappingRelation,
    Exam, Hall, Instructor, Schedule, AvailabilityDay, AvailabilityTime, InstructorOnHall
)
from .serializers import (
    AdminSerializer, StudentSerializer, CourseSerializer, ExamSerializer,
    HallSerializer, InstructorSerializer, ScheduleSerializer, CourseMappingsSerializer
)
from .authentication import CookieJWTAuthentication


# Admin Views
@api_view(['POST'])
@permission_classes([AllowAny])
def admin_register(request):
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    college = request.data.get('college')
    
    if Admin.objects.filter(email=email).exists():
        return Response({'message': 'البريد الإلكتروني مستخدم بالفعل.'}, status=status.HTTP_400_BAD_REQUEST)
    
    admin = Admin.objects.create(
        username=username,
        email=email,
        password=password,
        college=college
    )
    
    return Response({
        'message': 'تم إنشاء المشرف بنجاح.',
        'admin': {
            'id': admin.id,
            'username': admin.username,
            'email': admin.email,
            'college': admin.college
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@authentication_classes([]) 
@permission_classes([AllowAny])
def admin_login(request):
    email = request.data.get('email')
    password = request.data.get('password')
    
    try:
        admin = Admin.objects.get(email=email)
    except Admin.DoesNotExist:
        return Response({'message': 'البريد الإلكتروني أو كلمة المرور غير صحيحة.'}, status=status.HTTP_400_BAD_REQUEST)
    
    if not admin.check_password(password):
        return Response({'message': 'البريد الإلكتروني أو كلمة المرور غير صحيحة.'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Generate JWT tokens using SimpleJWT
    from .authentication import get_tokens_for_admin
    tokens = get_tokens_for_admin(admin)
    
    response = Response({
        'message': 'تم تسجيل الدخول بنجاح.',
        'email': admin.email,
        'college': admin.college,
        'access': tokens['access'],
        'refresh': tokens['refresh']
    }, status=status.HTTP_200_OK)
    
    # Set access token in cookie for cookie-based authentication
    response.set_cookie(
        key='token',
        value=tokens['access'],
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite='Lax',
        max_age=86400  # 1 day in seconds
    )
    
    return response


@api_view(['POST'])
@permission_classes([AllowAny])
def admin_logout(request):
    response = Response({'message': 'تم تسجيل الخروج بنجاح.'}, status=status.HTTP_200_OK)
    response.delete_cookie('token')
    return response


@api_view(['GET'])
@permission_classes([AllowAny])
def admin_list(request):
    admins = Admin.objects.all()
    serializer = AdminSerializer(admins, many=True)
    return Response(serializer.data)


# Student Views
@api_view(['GET'])
@permission_classes([AllowAny])
def student_list(request):
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 10))
    offset = (page - 1) * limit
    
    students = Student.objects.all()[offset:offset + limit]
    total_count = Student.objects.count()
    
    selection = []
    for student in students:
        courses = student.courses.all()
        if courses.exists():
            courses_str = ' / '.join([course.courseName for course in courses])
            selection.append({
                'studentID': student.studentID,
                'name': student.name,
                'email': student.email,
                'courses': courses_str
            })
    
    return Response({
        'students': selection,
        'totalStudent': total_count
    })


@api_view(['PUT'])
@permission_classes([AllowAny])
def student_search(request, studentID):
    students = Student.objects.filter(studentID__icontains=studentID)
    
    if not students.exists():
        return Response({'message': 'لا يوجد طلاب تطابقوا مع هذا الرقم'}, status=status.HTTP_404_NOT_FOUND)
    
    selection = []
    for student in students:
        courses = student.courses.all()
        if courses.exists():
            courses_str = ' / '.join([course.courseName for course in courses])
            selection.append({
                'studentID': student.studentID,
                'name': student.name,
                'email': student.email,
                'courses': courses_str
            })
    
    return Response(selection)


@api_view(['GET'])
@permission_classes([AllowAny])
def students_in_courses(request, course1, course2):
    course_ids = [int(course1), int(course2)]
    
    # Find students enrolled in both courses
    students = Student.objects.filter(
        courses__courseID__in=course_ids
    ).annotate(
        course_count=Count('courses', filter=Q(courses__courseID__in=course_ids))
    ).filter(course_count=2).distinct()
    
    selection = []
    for student in students:
        courses = student.courses.all()
        courses_str = ' / '.join([course.courseName for course in courses])
        selection.append({
            'studentID': student.studentID,
            'name': student.name,
            'email': student.email,
            'courses': courses_str
        })
    
    return Response(selection)


# Course Views
class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]


# Hall Views
class HallViewSet(viewsets.ModelViewSet):
    serializer_class = HallSerializer
    permission_classes = [AllowAny]
    def get_queryset(self):
        queryset = Course.objects.all()
        college = self.request.query_params.get('college')  # جلب قيمة الكلية من الـ query
        if college:
            queryset = queryset.filter(college=college)  # فلترة الكورسات بناءً على الكلية
        return queryset


# Course Mapping Views
class CourseMappingViewSet(viewsets.ModelViewSet):
    queryset = CourseMappings.objects.all()
    serializer_class = CourseMappingsSerializer
    permission_classes = [AllowAny]


# Exam Views
@api_view(['GET'])
@permission_classes([AllowAny])
def exam_list(request):
    college = request.GET.get('college')
    
    exams = Exam.objects.filter(date__isnull=True, college=college)
    selection_exams = Exam.objects.filter(date__isnull=False, college=college)
    
    selection = []
    for exam in selection_exams:
        conflict = conflict_student_count(exam.date, exam.time)
        selection.append({
            'examID': exam.examID,
            'name': exam.name,
            'date': exam.date,
            'time': exam.time,
            'conflict': conflict
        })
    
    return Response({
        'exams': ExamSerializer(exams, many=True).data,
        'selectionExams': selection
    })


def conflict_student_count(date, time):
    if not date:
        return 0
    
    conflicting_students = Schedule.objects.filter(
        examID__date=date,
        examID__time=time
    ).values('studentID').annotate(
        conflict_count=Count('scheduleID')
    ).filter(conflict_count__gt=1)
    
    return conflicting_students.count()


@api_view(['GET'])
@permission_classes([AllowAny])
def exam_halls(request, examID):
    halls = Hall.objects.filter(schedules__examID=examID).distinct()
    serializer = HallSerializer(halls, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def selection_exams(request):
    college = request.GET.get('college')
    selection_exams = Exam.objects.filter(date__isnull=False, college=college)
    
    selection = []
    for exam in selection_exams:
        count = Schedule.objects.filter(examID=exam).count()
        halls = Hall.objects.filter(schedules__examID=exam).distinct()
        
        hs = []
        instructors_list = []
        
        for hall in halls:
            instructors = Instructor.objects.filter(
                instructor_on_halls__examID=exam,
                instructor_on_halls__hallID=hall
            ).distinct()
            
            if instructors.exists():
                instructor_names = ' / '.join([inst.name for inst in instructors])
                instructors_list.append(f"{hall.name} ({instructor_names})")
            else:
                instructors_list.append(f"{hall.name} (بدون مراقب)")
            
            capacity_used = Schedule.objects.filter(hallID=hall, examID=exam).count()
            space_left = hall.capacity - capacity_used
            hs.append(f"{hall.name} {space_left}")
        
        without_halls = Schedule.objects.filter(examID=exam, hallID__isnull=True).count()
        
        selection.append({
            'examID': exam.examID,
            'name': exam.name,
            'date': str(exam.date) if exam.date else None,
            'time': str(exam.time) if exam.time else None,
            'num': count,
            'withoutHalls': without_halls,
            'hall': ' / '.join(hs),
            'invigilator': ' / '.join(instructors_list)
        })
    
    return Response(selection)


@api_view(['GET'])
@permission_classes([AllowAny])
def conflict_exams(request):
    exams = Exam.objects.filter(date__isnull=False).prefetch_related('schedules')
    
    conflicts = {}
    student_exam_times = {}
    
    for exam in exams:
        exam_datetime = f"{exam.date} {exam.time}"
        for schedule in exam.schedules.all():
            student_id = schedule.studentID.studentID
            if student_id not in student_exam_times:
                student_exam_times[student_id] = {}
            if exam_datetime not in student_exam_times[student_id]:
                student_exam_times[student_id][exam_datetime] = []
            student_exam_times[student_id][exam_datetime].append(exam.examID)
    
    for student_id, times in student_exam_times.items():
        for exam_datetime, exam_ids in times.items():
            if len(exam_ids) > 1:
                for exam_id in exam_ids:
                    if exam_id not in conflicts:
                        exam = exams.get(examID=exam_id)
                        conflicts[exam_id] = {
                            'examID': exam.examID,
                            'name': exam.name,
                            'date': exam.date,
                            'time': exam.time,
                            'studentList': set()
                        }
                    conflicts[exam_id]['studentList'].add(student_id)
    
    result = []
    for exam_id, data in conflicts.items():
        result.append({
            'examID': data['examID'],
            'name': data['name'],
            'date': str(data['date']),
            'time': str(data['time']),
            'conflict count': len(data['studentList']),
            'student': ' / '.join([str(s) for s in data['studentList']])
        })
    
    return Response(result)


# Instructor Views
@api_view(['GET'])
@permission_classes([AllowAny])
def instructor_list(request):
    instructors = Instructor.objects.all()
    serializer = InstructorSerializer(instructors, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def instructor_detail(request, id):
    try:
        instructor = Instructor.objects.get(instructorID=id)
        serializer = InstructorSerializer(instructor)
        return Response(serializer.data)
    except Instructor.DoesNotExist:
        return Response({'error': 'Instructor not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def instructor_create(request):
    name = request.data.get('name')
    email = request.data.get('email')
    days = request.data.get('days', [])
    
    if Instructor.objects.filter(email=email).exists():
        return Response({'error': 'البريد الإلكتروني مستخدم من قبل'}, status=status.HTTP_400_BAD_REQUEST)
    
    instructor = Instructor.objects.create(name=name, email=email)
    
    for day_data in days:
        availability_day = AvailabilityDay.objects.create(
            date=day_data['date'],
            instructorID=instructor
        )
        
        for time_data in day_data['time']:
            AvailabilityTime.objects.create(
                time=time_data['time'],
                availabilityId=availability_day
            )
    
    return Response({
        'message': f'تمت إضافة المراقب {instructor.name}'
    }, status=status.HTTP_201_CREATED)


@api_view(['PUT'])
@permission_classes([AllowAny])
def instructor_update(request, id):
    try:
        instructor = Instructor.objects.get(instructorID=id)
    except Instructor.DoesNotExist:
        return Response({'error': 'المراقب غير موجود'}, status=status.HTTP_404_NOT_FOUND)
    
    name = request.data.get('name')
    email = request.data.get('email')
    days = request.data.get('days', [])
    
    if email and email != instructor.email:
        if Instructor.objects.filter(email=email).exists():
            return Response({'error': 'البريد الإلكتروني مستخدم من قبل'}, status=status.HTTP_400_BAD_REQUEST)
    
    instructor.name = name
    instructor.email = email
    instructor.save()
    
    # Delete old availability
    availability_days = AvailabilityDay.objects.filter(instructorID=instructor)
    for day in availability_days:
        AvailabilityTime.objects.filter(availabilityId=day).delete()
    availability_days.delete()
    
    InstructorOnHall.objects.filter(instructorID=instructor).delete()
    
    # Create new availability
    for day_data in days:
        availability_day = AvailabilityDay.objects.create(
            date=day_data['date'],
            instructorID=instructor
        )
        
        for time_data in day_data['time']:
            AvailabilityTime.objects.create(
                time=time_data['time'],
                availabilityId=availability_day
            )
    
    return Response({
        'message': f'تم تحديث بيانات المراقب {instructor.name}'
    })


@api_view(['DELETE'])
@permission_classes([AllowAny])
def instructor_delete(request, id):
    try:
        instructor = Instructor.objects.get(instructorID=id)
        
        InstructorOnHall.objects.filter(instructorID=instructor).delete()
        
        availability_days = AvailabilityDay.objects.filter(instructorID=instructor)
        for day in availability_days:
            AvailabilityTime.objects.filter(availabilityId=day).delete()
        availability_days.delete()
        
        instructor.delete()
        
        return Response({'message': 'تم حذف المراقب وجميع مواعيده بنجاح'})
    except Instructor.DoesNotExist:
        return Response({'error': 'المراقب غير موجود'}, status=status.HTTP_404_NOT_FOUND)
