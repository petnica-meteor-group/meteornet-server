from django.db.models import Model, CharField, FloatField, IntegerField, TextField, ManyToManyField, \
                             DateTimeField, BooleanField, ForeignKey, CASCADE, SET_DEFAULT
from django.utils import timezone

class Person(Model):
    name = CharField(max_length=64, default='Test Person')
    phone = CharField(max_length=64, default='')
    email = CharField(max_length=64, default='')

class Status(Model):
    name = CharField(max_length=64, default='Test Status')
    color = CharField(max_length=16, default='#00CC00')
    severity = IntegerField(default=0)

def init_statuses():
    if Status.objects.all().count() == 0:
        data = [
                ("Good", '#00CC00'),
                ("Not connecting", '#FFFF19'),
                ("Rule(s) broken", '#FFA500'),
                ("Error(s) occured", '#CC0000'),
                ("Disconnected", '#990000'),
        ]
        for i, d in enumerate(data):
            status = Status()
            status.name = d[0]
            status.color = d[1]
            status.severity = i
            status.save()

def get_status_rule_broken():
    init_statuses()
    return Status.objects.get(name="Rule(s) broken").id

def get_status_default():
    init_statuses()
    return Status.objects.get(name="Good").id

class StatusRule(Model):
    expression = CharField(max_length=256)
    message = CharField(max_length=128)
    status = ForeignKey(Status, default=get_status_rule_broken, on_delete=CASCADE)

class Station(Model):
    network_id = CharField(max_length=64)
    name = CharField(max_length=64, default='Test Station')
    latitude = FloatField(default=0.0)
    longitude = FloatField(default=0.0)
    elevation = FloatField(default=0.0)
    comment = TextField(max_length=512, default='')
    maintainers = ManyToManyField(Person)
    last_updated = DateTimeField(default=timezone.now)
    approved = BooleanField(default=False)
    status = ForeignKey(Status, default=get_status_default, on_delete=SET_DEFAULT)

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
