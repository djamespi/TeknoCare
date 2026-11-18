from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.db.models.functions import Lower, Trim
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .identity import identity_matches, normalize_email, normalize_school_id


class UserManager(models.Manager):
	def get_by_natural_key(self, school_id):
		return identity_matches(self.get_queryset(), school_id=school_id).get()

	def create_user(self, school_id, email, password=None, **extra_fields):
		extra_fields.setdefault("user_type", User.UserType.PATIENT)
		extra_fields.setdefault("account_status", User.AccountStatus.ACTIVE)
		user = self.model(school_id=normalize_school_id(school_id), email=normalize_email(email), **extra_fields)
		user.set_password(password)
		user.save(using=self._db)
		return user

	def create_superuser(self, school_id, email, password=None, **extra_fields):
		extra_fields.setdefault("user_type", User.UserType.ADMIN)
		extra_fields.setdefault("account_status", User.AccountStatus.ACTIVE)
		if extra_fields["user_type"] != User.UserType.ADMIN or extra_fields["account_status"] != User.AccountStatus.ACTIVE:
			raise ValueError("A superuser must be an active Admin account.")
		return self.create_user(school_id, email, password, **extra_fields)


class User(models.Model):
	ADMIN_VIEW_PERMISSIONS = frozenset({"register.view_user", "profile.view_profile", "user_settings.view_usersettings"})

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

	created_at = models.DateTimeField(default=timezone.now, editable=False)

	objects = UserManager()

	USERNAME_FIELD = "school_id"
	REQUIRED_FIELDS = ["email"]

	class Meta:
		db_table = "user"
		constraints = [
			models.UniqueConstraint(Trim("school_id"), name="user_school_id_trim_unique"),
			models.UniqueConstraint(Lower(Trim("email")), name="user_email_casefold_unique"),
			models.CheckConstraint(check=models.Q(user_type__in=["Admin", "Patient", "Provider"]), name="user_role_valid"),
			models.CheckConstraint(check=models.Q(account_status__in=["Active", "Suspended"]), name="user_status_valid"),
		]

	def set_password(self, raw_password):
		self.password_hash = make_password(raw_password)

	def clean(self):
		self.school_id = normalize_school_id(self.school_id)
		self.email = normalize_email(self.email)

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


	@property
	def is_superuser(self):
		return False

	def get_full_name(self):
		return f"{self.fname} {self.lname}".strip()

	def get_short_name(self):
		return self.fname

	def natural_key(self):
		return (self.school_id,)

	def has_perm(self, perm, obj=None):
		return self.is_active and self.is_staff and perm in self.ADMIN_VIEW_PERMISSIONS

	def has_perms(self, perm_list, obj=None):
		return all(self.has_perm(perm, obj) for perm in perm_list)

	def has_module_perms(self, app_label):
		return any(self.has_perm(permission) for permission in self.ADMIN_VIEW_PERMISSIONS if permission.startswith(f"{app_label}."))

	def _get_session_auth_hash(self, secret=None):
		return salted_hmac("teknocare.User.session", self.password_hash, secret=secret, algorithm="sha256").hexdigest()

	def get_session_auth_hash(self):
		return self._get_session_auth_hash()

	def get_session_auth_fallback_hash(self):
		from django.conf import settings
		for secret in settings.SECRET_KEY_FALLBACKS:
			yield self._get_session_auth_hash(secret)
