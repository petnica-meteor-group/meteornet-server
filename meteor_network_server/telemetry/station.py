from django.db import models
from django.utils import timezone
from datetime import timedelta

import uuid

class Station(models.Model):
    id = models.CharField(max_length=32, primary_key=True)
    name = models.CharField(max_length=128, default="Unnamed Station")
    last_updated = models.DateTimeField(default=timezone.now)
    temperature = models.FloatField(default=0.0)
    humidity = models.FloatField(default=0.0)
    disk_used = models.FloatField(default=0.0)
    disk_cap = models.FloatField(default=0.0)

def get(id):
    return None

def register(data):
    id = uuid.uuid4().hex

    return id

def update(id, data):
    pass

def get_current_list():
    stations = []

    station = { 'name' : 'station1',
                'last_updated' : timezone.now() - timedelta(seconds=100),
                'temperature' : 32,
                'humidity' : 50,
                'disk_used' : 60,
                'disk_cap' : 100
            }
    stations.append(station)

    station = { 'name' : 'station2',
                'last_updated' : timezone.now() - timedelta(seconds=300),
                'temperature' : 15,
                'humidity' : 60,
                'disk_used' : 20,
                'disk_cap' : 120
            }
    stations.append(station)

    station = { 'name' : 'station3',
                'last_updated' : timezone.now() - timedelta(seconds=20),
                'temperature' : 20,
                'humidity' : 40,
                'disk_used' : 10,
                'disk_cap' : 70
            }
    stations.append(station)

    return stations
