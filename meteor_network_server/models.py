from django.db.models import Model, TextField

from .stations import models

class AdministrationNotes(Model):
    content = TextField(max_length=4096, default='')
