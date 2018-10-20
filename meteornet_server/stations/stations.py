from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.timezone import make_aware, localtime
from django.db import transaction, connection
from django.shortcuts import get_object_or_404
from django.core import mail
from django.core.validators import validate_email
from django.conf import settings
from django.core.exceptions import ValidationError

from datetime import timedelta, datetime
from os import path
import uuid
import json
import math
import matplotlib
matplotlib.use('WebAgg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import random
import ast
import re

from .models import *

MAX_UNAPPROVED_STATIONS = 30
RECENT_MEASUREMENTS_DAYS = 7
OLD_DATA_DAYS = 365
CURRENT_VALUES_WINDOW_HOURS = 3
DISCONNECTED_HOURS = 72
NOT_CONNECTING_HOURS = 6
NOTIFICATION_EMAIL = 'pmg@' + settings.DOMAIN_NAME

def get_current_list():
    return Station.objects.filter(approved=True)

def get_status(station):
    return station.status.name, station.status.color

def get_unapproved():
    return Station.objects.filter(approved=False)

def get(network_id):
    return get_object_or_404(Station, network_id=network_id)

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

def get_maintainers(station):
    return station.maintainers.all()

def extract_num_unit(string_value):
    string_value = str(string_value)
    num = float('NaN')
    cutout = len(string_value)
    for i in range(1, len(string_value) + 1):
        try:
            num = float(string_value[:i])
        except ValueError:
            cutout = i - 1
            break
    return num, string_value[cutout:]

def get_component_data(station):
    with transaction.atomic():
        component_data = []

        for component_object in Component.objects.filter(station=station.id):
            component = {}

            component['name'] = component_object.name

            batches = []
            for measurement_batch_object in MeasurementBatch.objects.filter(
            component=component_object.id,
            datetime__gt=(timezone.now() - timedelta(days=RECENT_MEASUREMENTS_DAYS))).order_by('datetime'):
                batch = { 'datetime' : localtime(measurement_batch_object.datetime), 'measurements' : [] }
                for measurement_object in Measurement.objects.filter(batch=measurement_batch_object.id):
                    batch['measurements'].append({ 'key' : measurement_object.key, 'value' : measurement_object.value })
                batches.append(batch)

            timedeltas = []
            for i in range(1, len(batches)):
                timedeltas.append(batches[i    ]['datetime'] -
                                  batches[i - 1]['datetime'])
            timedeltas = sorted(timedeltas)
            if len(timedeltas) == 0:
                median_timedelta = timedelta(0)
            else:
                median_timedelta = timedeltas[len(timedeltas) // 2]
            current_datetime = localtime(timezone.now())

            current_values_data = {}
            graphs_data = {}
            for batch in batches:
                recent_batch = (current_datetime - batch['datetime']).total_seconds() // 3600 < CURRENT_VALUES_WINDOW_HOURS

                for measurement in batch['measurements']:
                    key = measurement['key']
                    value = measurement['value']
                    if recent_batch:
                        num, unit = extract_num_unit(value)
                        if math.isnan(num):
                            current_values_data[key] = value
                        else:
                            current_values_data[key] = "{:8.2f}".format(num) + unit

                    if key in graphs_data:
                        data = graphs_data[key]
                        previous_datetime = data['values'][-1]['x'][-1]
                        current_datetime = batch['datetime']
                        if (current_datetime - previous_datetime) > 2.5 * median_timedelta:
                            data['values'].append({ 'x' : [], 'y' : [] })
                    else:
                        data = { 'values' : [ { 'x' : [], 'y' : [] } ], 'constant' : True }
                        graphs_data[key] = data

                    data['values'][-1]['x'].append(batch['datetime'])
                    if 'classes' in data:
                        if not (value in data['classes']):
                            data['class_ids'].append(data['class_ids'][-1] + 1)
                            data['classes'].append(value)
                        data['values'][-1]['y'].append(data['class_ids'][data['classes'].index(value)])
                        if len(data['values'][-1]['y']) >= 2 and \
                        (data['values'][-1]['y'][-1] != data['values'][-1]['y'][-2]):
                            data['constant'] = False
                    else:
                        if 'unit' in data:
                            previous_unit = data['unit']
                        else:
                            previous_unit = None
                        num, unit = extract_num_unit(value)
                        num = round(num, 2)
                        if (previous_unit != None and unit != previous_unit) or math.isnan(num):
                            data['class_ids'] = []
                            data['classes'] = []
                            for i in range(len(data['values'])):
                                for j in range(len(data['values'][i]['y'])):
                                    y = str(data['values'][i]['y'][j]) + data['unit']
                                    if not (y in data['classes']):
                                        new_id = data['class_ids'][-1] + 1 if len(data['class_ids']) > 0 else 1
                                        data['class_ids'].append(new_id)
                                        data['classes'].append(y)
                                    data['values'][i]['y'][j] = data['class_ids'][data['classes'].index(y)]
                            if not (value in data['classes']):
                                new_id = data['class_ids'][-1] + 1 if len(data['class_ids']) > 0 else 1
                                data['class_ids'].append(new_id)
                                data['classes'].append(value)
                            data['values'][-1]['y'].append(data['class_ids'][data['classes'].index(value)])
                            if 'unit' in data: del data['unit']
                            if len(data['values'][-1]['y']) >= 2 and \
                            (data['values'][-1]['y'][-1] != data['values'][-1]['y'][-2]):
                                data['constant'] = False
                        else:
                            data['values'][-1]['y'].append(num)
                            data['unit'] = unit
                            if len(data['values'][-1]['y']) >= 2 and \
                            (data['values'][-1]['y'][-1] != data['values'][-1]['y'][-2]):
                                data['constant'] = False

            constant_keys = []
            for key in graphs_data:
                if graphs_data[key]['constant']:
                    constant_keys.append(key)

            for key in constant_keys:
                del graphs_data[key]
                current_values_data[key] += " (constant)"

            component['current_values'] = list(current_values_data.items())

            graphs = []
            for key in graphs_data:
                graph = (station.network_id + component['name'] + key).replace(' ', '_') + '.png'
                data = graphs_data[key]
                color = [ random.uniform(0, 1), random.uniform(0, 1), random.uniform(0, 1) ]
                plt.figure(figsize=(12, 5))
                if 'classes' in data:
                    plt.yticks(data['class_ids'], data['classes'], size='x-large')
                else:
                    ax = plt.gca()
                    ax.yaxis.set_major_formatter(mticker.ScalarFormatter())
                    ax.yaxis.get_major_formatter().set_useOffset(False)
                if 'unit' in data: plt.ylabel(data['unit'], rotation='horizontal', size='x-large', labelpad=25)
                plt.title(key, size='xx-large')
                plt.tick_params(axis='x', which='major', labelsize='large')
                plt.tick_params(axis='y', which='major', labelsize='x-large')
                for xy in data['values']:
                    plt.plot(xy['x'], xy['y'], color=color)
                plt.savefig(path.join('/tmp', graph))
                plt.close()
                graphs.append(graph)
            component['graphs'] = graphs

            component_data.append(component)

        return component_data

def register(data):
    if Station.objects.filter(approved=False).count() >= MAX_UNAPPROVED_STATIONS:
        return ''

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

def notify_maintainers(station, rules_broken):
    emails = []
    for maintainer in station.maintainers.all():
        try:
            validate_email(maintainer.email)
            emails.append(maintainer.email)
        except ValidationError:
            pass

    subject = '[' + settings.SITE_NAME + '] Station notification'
    message = station.name + ' status changed to ' + station.status.name + '!\n\n'
    for rule_broken in rules_broken:
        message += '\t- ' + rule_broken.message + '\n'

    '''
    mail.send_mail(
        subject,
        message,
        NOTIFICATION_EMAIL,
        emails,
        fail_silently=False,
    )
    '''

def check_rule(station, rule):
    expression = rule.expression
    expression_prepared = list(expression)
    variable_regex = re.compile('\$\{([^}]*)\.([^}]*)\}')
    offset = 0
    for match in variable_regex.finditer(expression):
        component_name = match.group(1)
        member_name = match.group(2)

        value = None
        for component in Component.objects.filter(station=station.id):
            if component.name.lower().replace(' ', '_') == component_name.lower().replace(' ', '_'):
                for measurement_batch in MeasurementBatch.objects.filter(
                component=component.id,
                datetime__gt=(timezone.now() - timedelta(days=RECENT_MEASUREMENTS_DAYS))).order_by('datetime').reverse():
                    for measurement in Measurement.objects.filter(batch=measurement_batch.id):
                        if measurement.key.lower().replace(' ', '_') == member_name.lower().replace(' ', '_'):
                            value, _ = extract_num_unit(measurement.value)
                            break
        if value == None:
            return True

        expression_prepared[match.start() - offset : match.end() - offset] = str(value)
        offset += match.end() - match.start() - len(str(value))
    expression_prepared = ''.join(expression_prepared)

    return eval(expression_prepared)

def get_rules_broken(station):
    rules_broken = []
    for rule in StatusRule.objects.all():
        if not check_rule(station, rule):
            rules_broken.append(rule)
    return rules_broken

def update_status(station):
    previous_status = station.status
    rules_broken = []
    if (timezone.now() - station.last_updated).total_seconds() // 3600 > DISCONNECTED_HOURS:
        status = Status.objects.get(name="Disconnected")
    elif len(get_errors(station)) > 0:
        status = Status.objects.get(name="Error(s) occured")
    else:
        rules_broken = get_rules_broken(station)

        if len(rules_broken) > 0:
            status = Status.objects.get(name="Rule(s) broken")
        elif (timezone.now() - station.last_updated).total_seconds() // 3600 > NOT_CONNECTING_HOURS:
            status = Status.objects.get(name="Not connecting")
        else:
            status = Status.objects.all().first()
    station.status = status

    if station.status.severity > previous_status.severity:
        notify_maintainers(station, rules_broken)

    station.save()

def update_statuses():
    for station in Station.objects.filter(approved=True):
        update_status(station)

def delete_old_data():
    for measurement_batch in MeasurementBatch.objects.filter(
    datetime__lt=(timezone.now() - timedelta(days=OLD_DATA_DAYS))):
        measurement_batch.delete()

def new_data(data):
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

    update_status(station)
    return True

def get_version():
    from .station_code.internals import constants
    return constants.VERSION

def get_code_filepath():
    return path.join(path.dirname(__file__), 'station_code.zip')

def error_resolve(id):
    try:
        Error.objects.get(id=id).delete()
        return True
    except Exception:
        pass
    return False

def delete(network_id):
    try:
        Station.objects.get(network_id=network_id).delete()
        return True
    except Exception:
        pass
    return False

def get_graph_path(graph):
    return path.join('/tmp', graph)

def rule_delete(id):
    try:
        StatusRule.objects.get(id=id).delete()
        return True
    except Exception:
        pass
    return False

def rule_add(expression, message):
    try:
        if len(expression) > 256: return False
        if len(message) > 128: return False

        expression_prepared = list(expression)
        variable_regex = re.compile('\$\{([^}]*)\.([^}]*)\}')
        variable_count = 0
        offset = 0
        for match in variable_regex.finditer(expression):
            expression_prepared[match.start() - offset : match.end() - offset] = 'x'
            variable_count += 1
            offset += match.end() - match.start() - 1
        if variable_count == 0: return False
        expression_prepared = ''.join(expression_prepared)

        tree = ast.parse(expression_prepared)
        if not isinstance(tree.body[0], ast.Expr) or \
        (not isinstance(tree.body[0].value, ast.BoolOp) and not isinstance(tree.body[0].value, ast.Compare)):
            return False

        allowed_nodes = [
            ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Dict, ast.Set, ast.ListComp,
            ast.SetComp, ast.DictComp, ast.Compare, ast.Num, ast.Str, ast.NameConstant,
            ast.Constant, ast.Attribute, ast.Subscript, ast.Starred, ast.Name,
            ast.List, ast.Tuple, ast.Load, ast.Store, ast.AugLoad,
            ast.AugStore, ast.And, ast.Or, ast.Add, ast.Sub, ast.Mult, ast.MatMult, ast.Div,
            ast.Mod, ast.Pow, ast.LShift, ast.RShift, ast.BitOr, ast.BitXor,
            ast.BitAnd, ast.FloorDiv, ast.Invert, ast.Not, ast.UAdd, ast.USub,
            ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Is,
            ast.IsNot, ast.In, ast.NotIn
        ]

        class AllowedVisitor(ast.NodeVisitor):

            def __init__(self):
                self.allowed = True

            def generic_visit(self, node):
                found = False
                for allowed_node in allowed_nodes:
                    if isinstance(node, allowed_node):
                        found = True
                        break
                if not found:
                    self.allowed = False
                else:
                    ast.NodeVisitor.generic_visit(self, node)

        allowed_visitor = AllowedVisitor()
        allowed_visitor.visit(tree.body[0].value)
        if not allowed_visitor.allowed:
            return False

    except Exception:
        return False

    rule = StatusRule()
    rule.expression = expression
    rule.message = message
    rule.save()

    return True

def get_rules():
    return StatusRule.objects.all()
