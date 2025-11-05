from rest_framework import serializers
from .models import (
    Adminn, Student, Course, Enrollment, CourseMappings, CourseMappingRelation,
    Exam, Hall, Instructor, Schedule, AvailabilityDay, AvailabilityTime, InstructorOnHall
)


class AdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Adminn
        fields = ['id', 'username', 'email', 'password', 'college']
        extra_kwargs = {'password': {'write_only': True}}


class StudentSerializer(serializers.ModelSerializer):
    courses = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ['studentID', 'name', 'email', 'courses']

    def get_courses(self, obj):
        return ' / '.join([course.courseName for course in obj.courses.all()])


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['courseID', 'courseName', 'college']


class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = '__all__'


class CourseMappingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseMappings
        fields = ['mappingID', 'name']


class ExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = ['examID', 'name', 'date', 'time', 'college', 'courseID']


class HallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hall
        fields = ['hallID', 'name', 'capacity']


class InstructorSerializer(serializers.ModelSerializer):
    days = serializers.SerializerMethodField()

    class Meta:
        model = Instructor
        fields = ['instructorID', 'name', 'email', 'days']

    def get_days(self, obj):
        availability_days = obj.availability_days.all()
        days = []
        for day in availability_days:
            times = [{'time': slot.time} for slot in day.availability_slots.all()]
            days.append({'date': day.date, 'time': times})
        return days


class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = ['scheduleID', 'examID', 'studentID', 'hallID', 'college']


class AvailabilityDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilityDay
        fields = ['id', 'date', 'instructorID']


class AvailabilityTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilityTime
        fields = ['id', 'time', 'availabilityId']


class InstructorOnHallSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstructorOnHall
        fields = ['id', 'examID', 'hallID', 'instructorID']
