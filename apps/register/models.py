from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class UserManager(models.Manager):
	def get_by_natural_key(self, school_id):
		return self.get(**{User.USERNAME_FIELD: school_id})

	def create_user(self, school_id, email, password=None, **extra_fields):
		user = self.model(school_id=school_id, email=email, **extra_fields)
		user.set_password(password)
		user.save(using=self._db)
		return user

	def create_superuser(self, school_id, email, password=None, **extra_fields):
		extra_fields.setdefault("user_type", User.UserType.ADMIN)
		extra_fields.setdefault("account_status", User.AccountStatus.ACTIVE)
		return self.create_user(school_id, email, password, **extra_fields)


class User(models.Model):
	class UserType(models.TextChoices):
		ADMIN = "Admin", "Admin"
		PATIENT = "Patient", "Patient"
		PROVIDER = "Provider", "Provider"

	class AccountStatus(models.TextChoices):
		ACTIVE = "Active", "Active"
		SUSPENDED = "Suspended", "Suspended"

	user_id = models.AutoField(primary_key=True)
	school_id = models.CharField(max_length=20, unique=True)
	fname = models.CharField(max_length=50)
	lname = models.CharField(max_length=50)
	email = models.EmailField(max_length=100, unique=True)
	password_hash = models.CharField(max_length=255)
	user_type = models.CharField(max_length=10, choices=UserType.choices)
	account_status = models.CharField(max_length=10, choices=AccountStatus.choices)

	objects = UserManager()

	USERNAME_FIELD = "school_id"
	REQUIRED_FIELDS = ["email"]

	class Meta:
		db_table = "user"

	def set_password(self, raw_password):
		self.password_hash = make_password(raw_password)

	def check_password(self, raw_password):
		return check_password(raw_password, self.password_hash)

	@property
	def is_active(self):
		return self.account_status == self.AccountStatus.ACTIVE

	@property
	def is_staff(self):
		return self.user_type == self.UserType.ADMIN

	@property
	def is_authenticated(self):
		return True

	@property
	def is_anonymous(self):
		return False

	def get_username(self):
		return self.school_id

	def __str__(self):
		return f"{self.fname} {self.lname}".strip()


class Admin(models.Model):
	admin = models.OneToOneField(
		User,
		on_delete=models.CASCADE,
		primary_key=True,
		db_column="admin_id",
		related_name="admin_profile",
	)
	access_level = models.CharField(
		max_length=10,
		choices=[("Standard", "Standard"), ("Super", "Super")],
	)
	department = models.CharField(max_length=50)

	class Meta:
		db_table = "admin"


class Patient(models.Model):
	patient = models.OneToOneField(
		User,
		on_delete=models.CASCADE,
		primary_key=True,
		db_column="patient_id",
		related_name="patient_profile",
	)
	emergency_contact = models.CharField(max_length=100)
	medical_history_summary = models.TextField()
	no_show_count = models.IntegerField()

	class Meta:
		db_table = "patient"


class Provider(models.Model):
	provider = models.OneToOneField(
		User,
		on_delete=models.CASCADE,
		primary_key=True,
		db_column="provider_id",
		related_name="provider_profile",
	)
	specialization = models.CharField(max_length=100)
	room_number = models.CharField(max_length=10)
	is_active = models.BooleanField()

	class Meta:
		db_table = "provider"


class SupportTicket(models.Model):
	class Status(models.TextChoices):
		OPEN = "Open", "Open"
		IN_PROGRESS = "In-Progress", "In-Progress"
		RESOLVED = "Resolved", "Resolved"

	ticket_id = models.AutoField(primary_key=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="user_id")
	admin = models.ForeignKey(Admin, on_delete=models.CASCADE, db_column="admin_id")
	request_type = models.CharField(max_length=50)
	description = models.TextField()
	status = models.CharField(max_length=12, choices=Status.choices)

	class Meta:
		db_table = "support_ticket"


class AuditLog(models.Model):
	log_id = models.AutoField(primary_key=True)
	admin = models.ForeignKey(Admin, on_delete=models.CASCADE, db_column="admin_id")
	action_performed = models.CharField(max_length=100)
	target_table = models.CharField(max_length=50)
	target_record_id = models.IntegerField()
	logged_at = models.DateTimeField()

	class Meta:
		db_table = "audit_log"


class Slot(models.Model):
	slot_id = models.AutoField(primary_key=True)
	provider = models.ForeignKey(Provider, on_delete=models.CASCADE, db_column="provider_id")
	start_time = models.DateTimeField()
	end_time = models.DateTimeField()
	is_booked = models.BooleanField()

	class Meta:
		db_table = "slot"


class Appointment(models.Model):
	class Status(models.TextChoices):
		SCHEDULED = "Scheduled", "Scheduled"
		COMPLETED = "Completed", "Completed"
		CANCELED = "Canceled", "Canceled"
		NO_SHOW = "No Show", "No Show"

	appointment_id = models.AutoField(primary_key=True)
	patient = models.ForeignKey(Patient, on_delete=models.CASCADE, db_column="patient_id")
	provider = models.ForeignKey(Provider, on_delete=models.CASCADE, db_column="provider_id")
	slot = models.OneToOneField(Slot, on_delete=models.CASCADE, db_column="slot_id")
	reason_for_visit = models.CharField(max_length=255)
	status = models.CharField(max_length=10, choices=Status.choices)

	class Meta:
		db_table = "appointment"


class MedicalRecord(models.Model):
	record_id = models.AutoField(primary_key=True)
	appointment = models.OneToOneField(
		Appointment,
		on_delete=models.CASCADE,
		db_column="appointment_id",
	)
	patient = models.ForeignKey(Patient, on_delete=models.CASCADE, db_column="patient_id")
	provider = models.ForeignKey(Provider, on_delete=models.CASCADE, db_column="provider_id")
	symptoms = models.TextField()
	diagnosis = models.TextField()
	prescription_notes = models.TextField()
	created_at = models.DateTimeField()

	class Meta:
		db_table = "medical_record"
