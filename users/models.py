from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    class Meta:
        db_table = 'user'
        verbose_name_plural = 'users'
        verbose_name = 'user'

    def __str__(self):
        return f"{self.username}"