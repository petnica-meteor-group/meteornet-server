from django.db import models
from django.utils import timezone
from datetime import timedelta
from .hosts import Host

import uuid

class Station(models.Model):
    id = models.CharField(max_length=32, primary_key=True)
    name = models.CharField(max_length=128, default="Unnamed Station")
    temperature = models.FloatField(default=None)
    humidity = models.FloatField(default=None)
    disk_used = models.FloatField(default=None)
    disk_cap = models.FloatField(default=None)
    last_updated = models.DateTimeField(default=timezone.now)
    host = models.ForeignKey(Host, default=None, on_delete=models.CASCADE)

class TelemetryLog(models.Model):
    temperature = models.FloatField(default=None)
    humidity = models.FloatField(default=None)
    station = models.ForeignKey(Station, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=timezone.now)

def register(data):
    found_stations = Station.objects.filter(name=data['name'])

    if len(found_stations > 0):
        station = found_stations[0]
    else:
        id = uuid.uuid4().hex

        station = Station()
        station.id = id

    if 'name' in data: station.name = data['name']
    if 'temperature' in data: station.temperature = data['temperature']
    if 'humidity' in data: station.humidity = data['humidity']
    if 'disk_used' in data: station.disk_used = data['disk_used']
    if 'disk_cap' in data: station.disk_cap = data['disk_cap']
    station.save()

    return station.id

def get(id):
    return Station.objects.get(id=id)

def update(id, data):
    station = get(id)
    if 'name' in data: station.name = data['name']

    telemetry_log = TelemetryLog()
    telemetry_log.station = station
    if 'temperature' in data:
        station.temperature = data['temperature']
        telemetry_log.temperature = data['temperature']
    if 'humidity' in data:
        station.humidity = data['humidity']
        telemetry_log.humidity = data['humidity']
    telemetry_log.timestamp = timezone.now()
    telemetry_log.save()

    if 'disk_used' in data: station.disk_used = data['disk_used']
    if 'disk_cap' in data: station.disk_cap = data['disk_cap']
    station.last_updated = timezone.now()
    station.save()

def get_current_list():
    return Station.objects.all()
