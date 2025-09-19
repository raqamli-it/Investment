from django.core.validators import RegexValidator
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager

class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Users require an tin field')
        email = email
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


uzb_phone_validator = RegexValidator(
    regex=r'^\+998(33|50|55|77|88|90|91|93|94|95|97|98|99)\d{7}$',
    message="Telefon raqamni +99890XXXXXXX formatida kiriting."
)


class User(AbstractUser):
    phone_num = models.CharField('Phone number', max_length=13, unique=True, blank=True, null=True,
        validators=[uzb_phone_validator]
    )
    username = None
    email = models.EmailField(('email address'), unique=True)
    photo = models.ImageField(upload_to='files/users_photo/', blank=True, null=True)
    tin = models.CharField(max_length=14, unique=True)
    about = models.TextField(max_length=355, blank=True, null=True)
    is_physic = models.BooleanField(default=True)
    is_online = models.BooleanField(default=False)  # Online holat
    last_seen = models.DateTimeField(null=True, blank=True)  # oxirgi marta ko‘ringan vaqt

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

class EmailActivation(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_activation')
    email = models.EmailField(null=False, blank=False, max_length=128)
    token = models.CharField(max_length=64)
    date = models.DateTimeField(auto_now=True)
    resend_url_token = models.CharField(max_length=64)
    num_sent = models.PositiveIntegerField(default=0)
