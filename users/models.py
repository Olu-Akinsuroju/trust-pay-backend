from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    phone = models.CharField(max_length=15, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account_number = models.CharField(max_length=10, blank=True)
    bank_code = models.CharField(max_length=10, blank=True)
    bank_account_name = models.CharField(max_length=100, blank=True)
    is_merchant = models.BooleanField(default=False)
