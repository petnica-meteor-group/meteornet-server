from django.db.models import Model, CharField, FloatField, TextField, ManyToManyField, \
                             DateTimeField, BooleanField, ForeignKey, CASCADE

class Person(Model):
    name = CharField(max_length=64)
    phone = CharField(max_length=64, default='')
    email = CharField(max_length=64, default='')

class Station(Model):
    network_id = CharField(max_length=64)
    name = CharField(max_length=64)
    latitude = FloatField()
    longitude = FloatField()
    height = FloatField()
    comment = TextField(max_length=512, default='')
    maintainers = ManyToManyField(Person)
    last_updated = DateTimeField()
    approved = BooleanField(default=False)

class Component(Model):
    name = CharField(max_length=64)
    station = ForeignKey(Station, on_delete=CASCADE)
    old = BooleanField()

class MeasurementBatch(Model):
    datetime = DateTimeField()
    component = ForeignKey(Component, on_delete=CASCADE)

class Measurement(Model):
    key = CharField(max_length=128)
    value = CharField(max_length=128)
    batch = ForeignKey(MeasurementBatch, on_delete=CASCADE)

class Error(Model):
    message = TextField(max_length=512, default='')
    component = ForeignKey(Component, on_delete=CASCADE)
    datetime = DateTimeField()
