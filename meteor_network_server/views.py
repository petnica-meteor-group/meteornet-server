from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from wsgiref.util import FileWrapper

from datetime import datetime, timedelta
from os import path
import json
import math
import matplotlib
matplotlib.use('WebAgg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import PIL
import random

from .models import *
from .stations.models import *
from .stations import stations

RESPONSE_SUCCESS = "success"
RESPONSE_FAILURE = "failure"
STATIONS_PER_ROW = 4
MAINTAINERS_PER_ROW = 3
COMPONENT_CURRENT_VALUES_PER_ROW = 8
RECENT_BATCH_WINDOW_HOURS = 3
COMPONENT_PLOTS_PER_ROW = 1

@require_http_methods(["POST"])
def login(request):
    username = request.POST['username']
    password = request.POST['password']
    user = authenticate(request, username=username, password=password)
    if user is not None:
        django_login(request, user)
    else:
        messages.add_message(request, messages.ERROR, "Wrong credentials")
    return redirect('/')

@require_http_methods(["POST"])
def logout(request):
    django_logout(request)
    return redirect('/')

def format_last_updated(last_updated):
    minutes = int((timezone.now() - last_updated).total_seconds() // 60)
    if minutes < 1:
        return "Less than a minute ago."
    elif minutes == 1:
        return str(minutes) + " minute ago."
    elif minutes > 1 and minutes < 60:
        return str(minutes) + " minutes ago."
    else:
        hours = minutes // 60
        if hours == 1:
            return str(hours) + " hour ago."
        elif hours > 1 and hours < 24:
            return str(hours) + " hours ago."
        else:
            days = hours // 24
            if days == 1:
                return str(days) + " day ago."
            else:
                return str(days) + " days ago."
    return ""

@require_http_methods(["GET"])
def index(request):
    station_list = stations.get_current_list()

    station_coordinates = []
    center = { 'longitude' : 0, 'latitude' : 0 }
    count = 0
    for station in station_list:
        station_coordinates.append({ 'longitude' : station.longitude, 'latitude' : station.latitude })
        center['longitude'] += station.longitude
        center['latitude'] += station.latitude
        count += 1
    center['longitude'] /= count
    center['latitude'] /= count

    max_distance = 0
    for station in station_list:
        distance = math.sqrt(
            (center['longitude'] - station.longitude) ** 2 +
            (center['latitude'] - station.latitude) ** 2
        )
        if distance > max_distance:
            max_distance = distance

    if max_distance > 0:
        zoom_level = -math.log(256 * max_distance / 40000000 * 100)
        if zoom_level > 7: zoom_level = 7
    else:
        zoom_level = 7
    context = {
        'station_coordinates' : station_coordinates,
        'center' : center,
        'zoom_level' : zoom_level,
        'settings' : settings
    }
    return render(request, 'index.html', context)

@require_http_methods(["GET"])
@login_required
def stations_overview(request):
    station_list = stations.get_current_list()

    station_rows = []
    for i in range(0, len(station_list), STATIONS_PER_ROW):
        row = {}

        station_cards = []
        for j in range(STATIONS_PER_ROW):
            if i + j >= len(station_list): break

            station = station_list[i + j]

            station_card = {}
            station_card['network_id'] = station.network_id
            station_card['name'] = station.name
            station_card['latitude'] = station.latitude
            station_card['longitude'] = station.longitude
            station_card['height'] = station.height
            station_card['last_updated'] = format_last_updated(station.last_updated)

            if len(stations.get_errors(station)) > 0:
                status_text = "Error(s) occured!"
                status_color = 'red'
            elif (timezone.now() - station.last_updated).total_seconds() // 3600 > 6:
                status_text = "Not connecting"
                status_color = 'orange'
            elif (timezone.now() - station.last_updated).total_seconds() // 3600 > 72:
                status_text = "Disconnected"
                status_color = 'black'
            else:
                status_text = "Good"
                status_color = '#00CC00'

            station_card['status_text'] = status_text
            station_card['status_color'] = status_color

            station_cards.append(station_card)

        row['station_cards'] = station_cards
        row['col_size'] = 12 // STATIONS_PER_ROW

        station_rows.append(row)

    context = { 'station_rows' : station_rows, 'settings' : settings }
    return render(request, 'stations_overview.html', context)

@require_http_methods(["GET"])
@login_required
def administration(request):
    unapproved_stations = stations.get_unapproved()

    registration_requests_rows = []
    for i in range(0, len(unapproved_stations), STATIONS_PER_ROW):
        row = {}

        station_cards = []
        for j in range(STATIONS_PER_ROW):
            if i + j >= len(unapproved_stations): break

            station = unapproved_stations[i + j]

            station_card = {}
            station_card['network_id'] = station.network_id
            station_card['name'] = station.name
            station_card['latitude'] = station.latitude
            station_card['longitude'] = station.longitude
            station_card['height'] = station.height

            station_cards.append(station_card)

        row['station_cards'] = station_cards
        row['col_size'] = 12 // STATIONS_PER_ROW

        registration_requests_rows.append(row)

    if AdministrationNotes.objects.all().count() == 0:
        notes = AdministrationNotes()
        notes.content = ''
        notes.save()
    else:
        notes = AdministrationNotes.objects.all().first()

    context = { 'registration_requests_rows' : registration_requests_rows, 'notes' : notes.content, 'settings' : settings }
    return render(request, 'administration.html', context)

@require_http_methods(["POST"])
def administration_notes_update(request):
    notes = AdministrationNotes.objects.all().first()
    notes.content = request.POST.get('notes', '')
    notes.save()
    return redirect('/administration')

@require_http_methods(["GET"])
@login_required
def station_view(request, network_id):
    station = get_object_or_404(Station, network_id=network_id)
    measurements = stations.get_recent_measurements(station)
    errors = stations.get_errors(station)

    maintainers = list(station.maintainers.all().values())
    maintainer_rows = []
    for i in range(0, len(maintainers), MAINTAINERS_PER_ROW):
        row = {}

        maintainer_cards = []
        for j in range(MAINTAINERS_PER_ROW):
            if i + j >= len(maintainers): break

            maintainer = maintainers[i + j]

            maintainer_card = {}
            maintainer_card['name'] = maintainer['name']
            maintainer_card['phone'] = maintainer['phone']
            maintainer_card['email'] = maintainer['email']

            maintainer_cards.append(maintainer_card)

        row['maintainer_cards'] = maintainer_cards
        row['col_size'] = 12 // MAINTAINERS_PER_ROW
        row['sidecol_size'] = (12 - len(maintainer_cards) * row['col_size']) // 2

        maintainer_rows.append(row)

    components = []
    for component_measurement in measurements:
        component = {}
        component['name'] = component_measurement['component']

        timedeltas = []
        for i in range(1, len(component_measurement['batches'])):
            timedeltas.append(component_measurement['batches'][i    ]['datetime'] -
                              component_measurement['batches'][i - 1]['datetime'])
        timedeltas = sorted(timedeltas)
        if len(timedeltas) == 0:
            median_timedelta = timedelta(0)
        else:
            median_timedelta = timedeltas[len(timedeltas) // 2]
        current_datetime = timezone.now()

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

        current_values_data = {}
        plot_data = {}
        for batch in component_measurement['batches']:
            recent_batch = (current_datetime - batch['datetime']).total_seconds() // 3600 < RECENT_BATCH_WINDOW_HOURS

            for measurement in batch['measurements']:
                key = measurement['key']
                value = measurement['value']
                if recent_batch:
                    num, unit = extract_num_unit(value)
                    if math.isnan(num):
                        current_values_data[key] = value
                    else:
                        current_values_data[key] = "{:8.2f}".format(num) + unit

                if key in plot_data:
                    data = plot_data[key]
                    previous_datetime = data['values'][-1]['x'][-1]
                    current_datetime = batch['datetime']
                    if (current_datetime - previous_datetime) > 2.5 * median_timedelta:
                        data['values'].append({ 'x' : [], 'y' : [] })
                else:
                    data = { 'values' : [ { 'x' : [], 'y' : [] } ] }
                    plot_data[key] = data

                data['values'][-1]['x'].append(batch['datetime'])
                if 'classes' in data:
                    if not (value in data['classes']):
                        data['class_ids'].append(data['class_ids'][-1] + 1)
                        data['classes'].append(value)
                    data['values'][-1]['y'].append(data['class_ids'][data['classes'].index(value)])
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
                    else:
                        data['values'][-1]['y'].append(num)
                        data['unit'] = unit

        current_values = []
        for key in current_values_data:
            current_values.append((key, current_values_data[key]))

        plots = []
        for key in plot_data:
            plot = (station.network_id + component['name'] + key).replace(' ', '_') + '.png'
            data = plot_data[key]
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
            plt.savefig(path.join('/tmp', plot))
            plt.close()
            plots.append(plot)

        component['current_values_rows'] = []
        for i in range(0, len(current_values), COMPONENT_CURRENT_VALUES_PER_ROW):
            row = ''
            for j in range(COMPONENT_CURRENT_VALUES_PER_ROW):
                if i + j >= len(current_values): break
                key, value = current_values[i + j]
                row += key + ": " + str(value) + ", "
            row = row[:-len(", ")]
            component['current_values_rows'].append(row)

        component['plot_rows'] = []
        for i in range(0, len(plots), COMPONENT_PLOTS_PER_ROW):
            row = {}
            row_plots = []
            for j in range(COMPONENT_PLOTS_PER_ROW):
                if i + j >= len(plots): break
                row_plots.append(plots[i + j])

            row['plots'] = row_plots
            row['col_size'] = 12 // COMPONENT_PLOTS_PER_ROW
            row['sidecol_size'] = (12 - len(row_plots) * row['col_size']) // 2

            component['plot_rows'].append(row)

        components.append(component)

    context = {
        'station' : station,
        'maintainer_rows' : maintainer_rows,
        'components' : components,
        'errors' : errors,
        'settings' : settings
    }
    return render(request, 'station_view.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def station_register(request):
    return HttpResponse(stations.register(request.POST))

@require_http_methods(["POST"])
@login_required
def station_registration_resolve(request):
    stations.registration_resolve(request.POST.get('network_id', ''), request.POST.get('approve', None) == 'True')
    return redirect('/administration')

@csrf_exempt
@require_http_methods(["POST"])
def station_status(request):
    if stations.update_status(request.POST):
        return HttpResponse(RESPONSE_SUCCESS)
    else:
        return HttpResponse(RESPONSE_FAILURE)

@csrf_exempt
@require_http_methods(["POST"])
def station_version(request):
    return HttpResponse(stations.get_version())

@csrf_exempt
@require_http_methods(["POST"])
def station_update(request):
    with open(stations.get_update_filepath(), 'rb') as zipfile:
        wrapper = FileWrapper(zipfile)
        response = HttpResponse(wrapper, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename=station_code.zip'
        response['Content-Length'] = path.getsize(filepath)
        return response

@require_http_methods(["POST"])
@login_required
def station_error_resolve(request):
    stations.error_resolve(request.POST.get('error_id', ''))
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

@require_http_methods(["POST"])
@login_required
def station_delete(request):
    if stations.delete(request.POST.get('network_id', '')):
        return redirect('/stations_overview')
    else:
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

@require_http_methods(["GET"])
@login_required
def station_graph(request, graph):
    response = HttpResponse(content_type='image/png')
    graph = PIL.Image.open(path.join('/tmp', graph))
    graph.save(response, 'PNG')
    return response
