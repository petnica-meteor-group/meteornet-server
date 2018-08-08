from django.db import models

class Host(models.Model):
    name = models.CharField(max_length=128, default="Unnamed Host")
    email = models.CharField(max_length=128, default=None, null=True)
    phone = models.CharField(max_length=128, default=None, null=True)
    comment = models.TextField(max_length=512, default=None, null=True)
