from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import exam_views
from . import instructor_views
from . import upload_views
from . import print_views

router = DefaultRouter()
router.register(r'courses', views.CourseViewSet, basename='course')
router.register(r'halls', views.HallViewSet, basename='hall')
router.register(r'course-mappings', views.CourseMappingViewSet, basename='course-mapping')

urlpatterns = [
    # Admin routes
    path('admin/register', views.admin_register, name='admin-register'),
    path('admin/login', views.admin_login, name='admin-login'),
    path('admin/logout', views.admin_logout, name='admin-logout'),
    path('admin/', views.admin_list, name='admin-list'),
    
    # Student routes
    path('student/', views.student_list, name='student-list'),
    path('student/<str:studentID>', views.student_search, name='student-search'),
    path('student/courses-in-schedule/<str:course1>/<str:course2>', views.students_in_courses, name='students-in-courses'),
    
    # Exam routes
    path('exam/', views.exam_list, name='exam-list'),
    path('exam/exam-halls/<int:examID>', views.exam_halls, name='exam-halls'),
    path('exam/selection-exams', views.selection_exams, name='selection-exams'),
    path('exam/conflict-exams', views.conflict_exams, name='conflict-exams'),
    path('exam/update/<int:id>', exam_views.exam_update, name='exam-update'),
    path('exam/<int:id>', exam_views.exam_delete, name='exam-delete'),
    path('exam/select-hall/<int:examID>', exam_views.exam_select_hall, name='exam-select-hall'),
    path('exam/schedule-exams', exam_views.schedule_exams_auto, name='exam-schedule-auto'),
    path('exam/exam-schedules', exam_views.exam_schedules, name='exam-schedules'),
    path('exam/exam-hall-invigilators', exam_views.exam_hall_invigilators, name='exam-hall-invigilators'),
    
    # Instructor routes
    path('Instructor/', views.instructor_list, name='instructor-list'),
    path('Instructor/<int:id>', views.instructor_detail, name='instructor-detail'),
    path('Instructor/create', views.instructor_create, name='instructor-create'),
    path('Instructor/update/<int:id>', views.instructor_update, name='instructor-update'),
    path('Instructor/delete/<int:id>', views.instructor_delete, name='instructor-delete'),
    path('Instructor/selection-halls', instructor_views.selection_halls, name='instructor-selection-halls'),
    path('Instructor/invigilator-exist/<int:examID>', instructor_views.invigilator_exist, name='instructor-invigilator-exist'),
    path('Instructor/select-instructor/<str:hall>/<int:examID>', instructor_views.select_instructor, name='instructor-select'),
    path('Instructor/instructors-for-exam-and-hall-delete', instructor_views.instructors_for_exam_and_hall_delete, name='instructor-delete-assignment'),
    path('Instructor/instructors-for-exam-and-hall/<int:examID>/<int:hallID>', instructor_views.instructors_for_exam_and_hall, name='instructor-exam-hall'),
    
    # Upload routes
    path('upload/students', upload_views.upload_students, name='upload-students'),
    path('upload/courses', upload_views.upload_courses, name='upload-courses'),
    path('upload/enrollments', upload_views.upload_enrollments, name='upload-enrollments'),
    path('upload/halls', upload_views.upload_halls, name='upload-halls'),
    
    # Print routes
    path('print/exam-schedule', print_views.print_exam_schedule, name='print-exam-schedule'),
    path('print/student-schedule/<int:studentID>', print_views.print_student_schedule, name='print-student-schedule'),
    path('print/hall-schedule/<int:hallID>', print_views.print_hall_schedule, name='print-hall-schedule'),
    
    # Include router URLs
    path('', include(router.urls)),
]
