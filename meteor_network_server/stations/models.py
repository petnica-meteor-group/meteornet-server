from django.db.models import Model, CharField, FloatField, TextField, ManyToManyField, \
                             DateTimeField, BooleanField, ForeignKey, CASCADE, SET_DEFAULT
from django.utils import timezone

from .status_models import *

class Person(Model):
    name = CharField(max_length=64, default='Test Person')
    phone = CharField(max_length=64, default='')
    email = CharField(max_length=64, default='')

class Station(Model):
    network_id = CharField(max_length=64)
    name = CharField(max_length=64, default='Test Station')
    latitude = FloatField(default=0.0)
    longitude = FloatField(default=0.0)
    height = FloatField(default=0.0)
    comment = TextField(max_length=512, default='')
    maintainers = ManyToManyField(Person)
    last_updated = DateTimeField(default=timezone.now)
    approved = BooleanField(default=False)
    status = ForeignKey(Status, default=lambda: Status.objects.first(), on_delete=SET_DEFAULT)

class Component(Model):
    name = CharField(max_length=64, default='Test Component')
    station = ForeignKey(Station, on_delete=CASCADE)
    old = BooleanField(default=False)

class MeasurementBatch(Model):
    datetime = DateTimeField(default=timezone.now)
    component = ForeignKey(Component, on_delete=CASCADE)

class Measurement(Model):
    key = CharField(max_length=128, default='')
    value = CharField(max_length=128, default='')
    batch = ForeignKey(MeasurementBatch, on_delete=CASCADE)

class Error(Model):
    message = TextField(max_length=512, default='')
    component = ForeignKey(Component, on_delete=CASCADE)
    datetime = DateTimeField(default=timezone.now)
