from django.db import models
from django.utils import timezone
from datetime import timedelta

import uuid

class Station(models.Model):
    id = models.CharField(max_length=32, primary_key=True)
    name = models.CharField(max_length=128, default="Unnamed Station")
    temperature = models.FloatField(default=float('nan'))
    humidity = models.FloatField(default=float('nan'))
    disk_used = models.FloatField(default=float('nan'))
    disk_cap = models.FloatField(default=float('nan'))
    last_updated = models.DateTimeField(default=timezone.now)

def register(data):
    id = uuid.uuid4().hex

    station = Station()
    station.id = id
    if 'name' in data: station.name = data['name']
    if 'temperature' in data: station.temperature = data['temperature']
    if 'humidity' in data: station.humidity = data['humidity']
    if 'disk_used' in data: station.disk_used = data['disk_used']
    if 'disk_cap' in data: station.disk_cap = data['disk_cap']
    station.save()

    return id

def get(id):
    return Station.objects.get(id=id)

def update(id, data):
    station = get(id)
    if 'name' in data: station.name = data['name']
    if 'temperature' in data: station.temperature = data['temperature']
    if 'humidity' in data: station.humidity = data['humidity']
    if 'disk_used' in data: station.disk_used = data['disk_used']
    if 'disk_cap' in data: station.disk_cap = data['disk_cap']
    station.last_updated = timezone.now()
    station.save()

def get_current_list():
    return Station.objects.all()
