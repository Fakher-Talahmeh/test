from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class Adminn(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    college = models.CharField(max_length=255)

    class Meta:
        db_table = 'admins'

    def save(self, *args, **kwargs):
        # Hash password before saving if it's not already hashed
        if self.password and not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)


class Student(models.Model):
    studentID = models.AutoField(primary_key=True, db_column='studentID')
    name = models.CharField(max_length=255)
    email = models.EmailField()

    class Meta:
        db_table = 'students'


class Course(models.Model):
    courseID = models.AutoField(primary_key=True, db_column='courseID')
    courseName = models.CharField(max_length=255, db_column='courseName')
    college = models.CharField(max_length=255)
    students = models.ManyToManyField(Student, through='Enrollment', related_name='courses')

    class Meta:
        db_table = 'courses'


class Enrollment(models.Model):
    id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, db_column='studentStudentID')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, db_column='courseCourseID')
    createdAt = models.DateTimeField(auto_now_add=True, db_column='createdAt')
    updatedAt = models.DateTimeField(auto_now=True, db_column='updatedAt')

    class Meta:
        db_table = 'Enrollment'
        unique_together = ('student', 'course')


class CourseMappings(models.Model):
    mappingID = models.AutoField(primary_key=True, db_column='mappingID')
    name = models.CharField(max_length=255)
    courses = models.ManyToManyField(Course, through='CourseMappingRelation', related_name='course_mappings')

    class Meta:
        db_table = 'course_mappings'


class CourseMappingRelation(models.Model):
    id = models.AutoField(primary_key=True)
    course_mapping = models.ForeignKey(CourseMappings, on_delete=models.CASCADE, db_column='mappingID')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, db_column='courseID')
    createdAt = models.DateTimeField(auto_now_add=True, db_column='createdAt')
    updatedAt = models.DateTimeField(auto_now=True, db_column='updatedAt')

    class Meta:
        db_table = 'course_mapping_relations'
        unique_together = ('course_mapping', 'course')


class Exam(models.Model):
    examID = models.AutoField(primary_key=True, db_column='examID')
    name = models.CharField(max_length=255)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    college = models.CharField(max_length=255)
    courseID = models.ForeignKey(Course, on_delete=models.CASCADE, db_column='courseID', related_name='exams')

    class Meta:
        db_table = 'exams'


class Hall(models.Model):
    hallID = models.AutoField(primary_key=True, db_column='hallID')
    name = models.CharField(max_length=255)
    capacity = models.IntegerField()

    class Meta:
        db_table = 'halls'


class Instructor(models.Model):
    instructorID = models.AutoField(primary_key=True, db_column='instructorID')
    name = models.CharField(max_length=255)
    email = models.EmailField()

    class Meta:
        db_table = 'instructors'


class Schedule(models.Model):
    scheduleID = models.AutoField(primary_key=True, db_column='scheduleID')
    examID = models.ForeignKey(Exam, on_delete=models.CASCADE, db_column='examID', related_name='schedules', null=True)
    studentID = models.ForeignKey(Student, on_delete=models.CASCADE, db_column='studentID', related_name='schedules', null=True)
    hallID = models.ForeignKey(Hall, on_delete=models.CASCADE, db_column='hallID', related_name='schedules', null=True, blank=True)
    college = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'schedules'
        unique_together = ('examID', 'studentID')


class AvailabilityDay(models.Model):
    id = models.AutoField(primary_key=True)
    date = models.CharField(max_length=20)
    instructorID = models.ForeignKey(Instructor, on_delete=models.CASCADE, db_column='instructorID', related_name='availability_days')
    createdAt = models.DateTimeField(auto_now_add=True, db_column='createdAt')
    updatedAt = models.DateTimeField(auto_now=True, db_column='updatedAt')

    class Meta:
        db_table = 'availability_days'


class AvailabilityTime(models.Model):
    id = models.AutoField(primary_key=True)
    time = models.CharField(max_length=20)
    availabilityId = models.ForeignKey(AvailabilityDay, on_delete=models.CASCADE, db_column='availabilityId', related_name='availability_slots')
    createdAt = models.DateTimeField(auto_now_add=True, db_column='createdAt')
    updatedAt = models.DateTimeField(auto_now=True, db_column='updatedAt')

    class Meta:
        db_table = 'availability_times'


class InstructorOnHall(models.Model):
    id = models.AutoField(primary_key=True)
    examID = models.ForeignKey(Exam, on_delete=models.CASCADE, db_column='examID', related_name='instructor_on_halls')
    hallID = models.ForeignKey(Hall, on_delete=models.CASCADE, db_column='hallID', related_name='instructor_on_halls')
    instructorID = models.ForeignKey(Instructor, on_delete=models.CASCADE, db_column='instructorID', related_name='instructor_on_halls')
    createdAt = models.DateTimeField(auto_now_add=True, db_column='createdAt')
    updatedAt = models.DateTimeField(auto_now=True, db_column='updatedAt')

    class Meta:
        db_table = 'instructor_on_halls'
        unique_together = ('examID', 'hallID', 'instructorID')
