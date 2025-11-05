from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(Adminn)
admin.site.register(Schedule)
admin.site.register(Student)
admin.site.register(Enrollment)
admin.site.register(Course)
admin.site.register(CourseMappings)
admin.site.register(CourseMappingRelation)
admin.site.register(Exam)
admin.site.register(Hall)
admin.site.register(Instructor)
admin.site.register(AvailabilityDay)
admin.site.register(AvailabilityTime)
admin.site.register(InstructorOnHall)