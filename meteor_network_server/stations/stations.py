from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.utils.timezone import make_aware
from django.db import transaction, connection
from datetime import timedelta, datetime
from .models import *
import uuid
import json

MAX_UNAPPROVED_STATIONS = 30
RECENT_MEASUREMENTS_DAYS = 7

def register(data):
    if Station.objects.filter(approved=False).count() >= MAX_UNAPPROVED_STATIONS:
        return ''

    data = data.get('status', None)
    if data == None: return ''
    data = json.loads(data)

    station = Station()
    for key in data:
        if type(data[key]) is list or type(data[key]) is dict:
            continue
        elif hasattr(station, key):
            try:
                value = data[key]
                value = type(getattr(station, key))(value)
                setattr(station, key, value)
            except ValueError:
                pass
    if 'timestamp' in data: station.last_updated = make_aware(datetime.fromtimestamp(int(data['timestamp'])))
    network_id = uuid.uuid4().hex
    station.network_id = network_id
    station.approved = False
    station.save()

    return network_id

def update_status(data):
    data = data.get('status', None)
    if data == None: return False
    data = json.loads(data)

    try:
        station = Station.objects.get(network_id=data['network_id'])
        if not station.approved:
            return True
    except Exception:
        return False

    if 'error' in data:
        if 'component' in data:
            error = Error()
            for component in Component.objects.filter(station=station.id):
                if component.name == data['component']:
                    error.component = component
                    break
            error.message = data['error']
            if 'timestamp' in data:
                error.datetime = make_aware(datetime.fromtimestamp(int(data['timestamp'])))
            else:
                error.datetime = datetime.now()
            error.save()
        else:
            return False
    else:
        with transaction.atomic():
            for key in data:
                if type(data[key]) is list or type(data[key]) is dict:
                    continue
                elif hasattr(station, key):
                    try:
                        value = data[key]
                        value = type(getattr(station, key))(value)
                        setattr(station, key, value)
                    except ValueError:
                        pass
            if 'timestamp' in data: station.last_updated = make_aware(datetime.fromtimestamp(int(data['timestamp'])))

            components = Component.objects.filter(station=station.id)
            for component in components:
                component.old = True

            if 'components' in data:
                for component_data in data['components']:
                    if not 'name' in component_data: continue

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

                    if 'timestamp' in data and 'measurements' in component_data:
                        batch = MeasurementBatch()
                        batch.datetime = make_aware(datetime.fromtimestamp(int(data['timestamp'])))
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

            with transaction.atomic():
                connection.cursor().execute('LOCK {}'.format(Person._meta.db_table))

                existing_maintainers = station.maintainers.all()
                found_maintainers = []
                new_maintainers_data = []
                if 'maintainers' in data:
                    for maintainer_data in data['maintainers']:
                        maintainer = None
                        for existing_maintainer in existing_maintainers:
                            same = True
                            for key in maintainer_data:
                                try:
                                    if hasattr(existing_maintainer, key):
                                        if getattr(existing_maintainer, key) != type(getattr(existing_maintainer, key))(maintainer_data[key]):
                                            same = False
                                            break
                                    else:
                                        same = False
                                        break
                                except ValueError:
                                    same = False
                                    break
                            if same:
                               maintainer = existing_maintainer
                               break
                        if maintainer != None:
                            found_maintainers.append(maintainer)
                        else:
                            new_maintainers_data.append(maintainer_data)
                for maintainer in existing_maintainers:
                    if not maintainer in found_maintainers:
                        station.maintainers.remove(maintainer)
                        if maintainer.station_set.all().count() == 0:
                            maintainer.delete()

                persons = Person.objects.all()
                for new_maintainer_data in new_maintainers_data:
                    found = False
                    for person in persons:
                        same = True
                        for key in new_maintainer_data:
                            try:
                                if hasattr(person, key):
                                    if getattr(person, key) != type(getattr(person, key))(new_maintainer_data[key]):
                                        same = False
                                        break
                                else:
                                    same = False
                                    break
                            except ValueError:
                                same = False
                                break
                        if same:
                            station.maintainers.add(person)
                            found = True
                            break
                    if not found:
                        maintainer = Person()
                        for key in new_maintainer_data:
                            if hasattr(maintainer, key):
                                try:
                                    value = new_maintainer_data[key]
                                    value = type(getattr(maintainer, key))(value)
                                    setattr(maintainer, key, value)
                                except ValueError:
                                    pass
                        maintainer.save()
                        station.maintainers.add(maintainer)

            station.save()

    return True

def registration_resolve(network_id, approve):
    try:
        station = Station.objects.get(network_id=network_id)
        if approve:
            station.approved = approve
            station.save()
        else:
            station.delete()
        return True
    except Station.DoesNotExit:
        pass
    return False

def delete(network_id):
    try:
        station = Station.objects.get(network_id=network_id)
        station.delete()
        return True
    except Station.DoesNotExit:
        pass
    return False

def get_current_list():
    return Station.objects.filter(approved=True)

def get_unapproved():
    return Station.objects.filter(approved=False)

def get_errors(station):
    errors = []
    for component_object in Component.objects.filter(station=station.id):
        for error_object in Error.objects.filter(component=component_object.id):
            errors.append({
                'id' : error_object.id,
                'component' : component_object.name,
                'message' : error_object.message,
                'datetime' : error_object.datetime
            })
    return errors

def error_resolve(id):
    Error.objects.get(id=id).delete()

def get_maintainers(station):
    return station.maintainers.all()

def get_recent_measurements(station):
    measurements = []
    for component_object in Component.objects.filter(station=station.id):
        component_measurements = { 'component' : component_object.name, 'batches' : [] }
        for measurement_batch_object in MeasurementBatch.objects.filter(
        component=component_object.id, datetime__gt=(timezone.now() - timedelta(days=RECENT_MEASUREMENTS_DAYS))):
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
