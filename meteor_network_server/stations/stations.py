from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from datetime import timedelta, datetime
from .models import *
import uuid
import json

def update_data(station, data):
    if 'error' in data:
        error = Error()
        station = Station.objects.get(network_id=data['network_id'])
        for component in Component.objects.filter(station=station.id):
            if component.name == data['component']:
                error.component = component
                break
        error.message = data['error']
        error.save()
    else:
        if 'timestamp' in data: station.last_updated = datetime.fromtimestamp(int(data['timestamp']))
        if 'name' in data: station.name = data['name']
        if 'latitude' in data: station.latitude = float(data['latitude'])
        if 'longitude' in data: station.longitude = float(data['longitude'])
        if 'height' in data: station.height = float(data['height'])
        if 'comment' in data: station.comment = data['comment']
        station.save()

        components = Component.objects.filter(station=station.id)
        for component in components:
            component.old = True

        if 'components' in data:
            for component_data in json.loads(data['components']):
                target_component = None
                for component in components:
                    if component.name == component_data['name']:
                        target_component = component
                        break
                if target_component == None:
                    target_component = Component()
                    target_component.name = component_data['name']
                    target_component.station = station
                    target_component.old = False
                    target_component.save()
                batch = MeasurementBatch()
                batch.datetime = datetime.fromtimestamp(int(data['timestamp']))
                batch.component = target_component
                batch.save()
                for key in component_data['measurements']:
                    measurement = Measurement()
                    measurement.key = key
                    measurement.value = component_data['measurements'][key]
                    measurement.batch = batch
                    measurement.save()

        for component in components:
            component.save()

        old_maintainers = list(station.maintainers.all().values())
        new_maintainers_data = []
        if 'maintainers' in data:
            for maintainer_data in json.loads(data['maintainers']):
                maintainer = None
                for old_maintainer in old_maintainers:
                    if old_maintainer['name'] == maintainer_data['name'] and \
                    old_maintainer['phone'] == maintainer_data['phone'] and \
                    old_maintainer['email'] == maintainer_data['email']:
                       maintainer = old_maintainer
                       break
                if maintainer != None:
                    old_maintainers.remove(maintainer)
                else:
                    new_maintainers_data.append(maintainer_data)
        for old_maintainer in old_maintainers:
            station.maintainers.remove(old_maintainer)

        persons = Person.objects.all()
        for new_maintainer_data in new_maintainers_data:
            found = False
            for person in persons:
                if person.name == new_maintainer_data['name'] and \
                person.phone == new_maintainer_data['phone'] and \
                person.email == new_maintainer_data['email']:
                    station.maintainers.add(person)
                    found = True
            if not found:
                maintainer = Person()
                maintainer.name = new_maintainer_data['name']
                maintainer.phone = new_maintainer_data['phone']
                maintainer.email = new_maintainer_data['email']
                maintainer.save()
                station.maintainers.add(maintainer)

        station.save()

def register(data):
    try:
        station = Station.objects.get(name=data.get('name', ''))
        network_id = station.network_id
    except Station.DoesNotExist:
        station = Station()
        network_id = uuid.uuid4().hex
        station.network_id = network_id
    update_data(station, data)
    return network_id

def update_status(data):
    try:
        station = Station.objects.get(network_id=data.get('network_id', ''))
    except Station.DoesNotExist:
        return False
    update_data(station, data)
    return True

def get_current_list():
    return Station.objects.all()

def get_errors(station):
    errors = []
    for component_object in Component.objects.filter(station=station.id):
        for error_object in Error.objects.filter(component=component_object.id):
            errors.append({ 'component' : component_object.name, 'message' : error_object.message })
    return errors

def get_maintainers(station):
    return station.maintainers.all()

def get_recent_measurements(station):
    measurements = []
    for component_object in Component.objects.filter(station=station.id):
        component_measurements = { 'component' : component_object.name, 'batches' : [] }
        for measurement_batch_object in MeasurementBatch.objects.filter(
        component=component_object.id, datetime__gt=(timezone.now() - timedelta(days=3))):
            batch = { 'datetime' : measurement_batch_object.datetime, 'measurements' : [] }
            for measurement_object in Measurement.objects.filter(batch=measurement_batch_object.id):
                batch['measurements'].append({ 'key' : measurement_object.key, 'value' : measurement_object.value })
            component_measurements['batches'].append(batch)
        measurements.append(component_measurements)
    return measurements

def get_version():
    from .station_code.internals import constants
    return constants.VERSION

def get_update_filepath():
    return path.join(path.dirname(__file__), 'station_code.zip')
