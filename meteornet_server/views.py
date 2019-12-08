from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from wsgiref.util import FileWrapper

from os import path
import PIL
import json
import math

from .models import *
from .stations import stations

RESPONSE_SUCCESS = "success"
RESPONSE_FAILURE = "failure"
STATIONS_PER_ROW = 4
MAINTAINERS_PER_ROW = 3
COMPONENT_CURRENT_VALUES_PER_ROW = 8
COMPONENT_GRAPHS_PER_ROW = 1

@require_http_methods(["POST"])
def login(request):
    username = request.POST.get('username', '')
    password = request.POST.get('password', '')
    user = authenticate(request, username=username, password=password)
    if user is not None:
        django_login(request, user)
    else:
        messages.add_message(request, messages.ERROR, "Wrong credentials")
    return redirect('/')

@require_http_methods(["POST"])
@login_required
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
    station_coordinates = []
    center = { 'longitude' : 0, 'latitude' : 0 }
    zoom_level = 1

    station_list = stations.get_current_list()
    if len(station_list) > 0:
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
            station_card['elevation'] = station.elevation
            station_card['last_updated'] = format_last_updated(station.last_updated)

            status_text, status_color = stations.get_status(station)
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
            station_card['elevation'] = station.elevation

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

    warnings = stations.get_warnings()

    context = {
        'registration_requests_rows' : registration_requests_rows,
        'notes' : notes.content,
        'warnings' : warnings,
        'settings' : settings }
    return render(request, 'administration.html', context)

@require_http_methods(["POST"])
@login_required
def administration_notes_update(request):
    notes = AdministrationNotes.objects.all().first()
    notes.content = request.POST.get('notes', '')
    notes.save()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

@require_http_methods(["GET"])
@login_required
def station_view(request, network_id):
    station = stations.get(network_id)
    errors = stations.get_errors(station)
    maintainers = stations.get_maintainers(station)

    maintainer_rows = []
    for i in range(0, len(maintainers), MAINTAINERS_PER_ROW):
        row = {}

        maintainer_cards = []
        for j in range(MAINTAINERS_PER_ROW):
            if i + j >= len(maintainers): break

            maintainer = maintainers[i + j]

            maintainer_card = {}
            maintainer_card['name'] = maintainer.name
            maintainer_card['phone'] = maintainer.phone
            maintainer_card['email'] = maintainer.email

            maintainer_cards.append(maintainer_card)

        row['maintainer_cards'] = maintainer_cards
        row['col_size'] = 12 // MAINTAINERS_PER_ROW
        row['sidecol_size'] = (12 - len(maintainer_cards) * row['col_size']) // 2

        maintainer_rows.append(row)

    component_data = stations.get_component_data(station)

    for component in component_data:
        current_values = component['current_values']
        component['current_values_rows'] = []
        for i in range(0, len(current_values), COMPONENT_CURRENT_VALUES_PER_ROW):
            row = ''
            for j in range(COMPONENT_CURRENT_VALUES_PER_ROW):
                if i + j >= len(current_values): break
                key, value = current_values[i + j]
                row += key + ": " + str(value) + ", "
            row = row[:-len(", ")]
            component['current_values_rows'].append(row)

        graphs = component['graphs']
        component['graphs_rows'] = []
        for i in range(0, len(graphs), COMPONENT_GRAPHS_PER_ROW):
            row = {}
            row_graphs = []
            for j in range(COMPONENT_GRAPHS_PER_ROW):
                if i + j >= len(graphs): break
                row_graphs.append(graphs[i + j])

            row['graphs'] = row_graphs
            row['col_size'] = 12 // COMPONENT_GRAPHS_PER_ROW
            row['sidecol_size'] = (12 - len(row_graphs) * row['col_size']) // 2

            component['graphs_rows'].append(row)

    warnings_issued = stations.get_warnings_issued(station)

    context = {
        'station' : station,
        'maintainer_rows' : maintainer_rows,
        'component_data' : component_data,
        'errors' : errors,
        'warnings_issued' : warnings_issued,
        'settings' : settings
    }
    return render(request, 'station_view.html', context)

@require_http_methods(["POST"])
@csrf_exempt
def station_register(request):
    data = request.POST.get('json', None)
    if data == None: return HttpResponse(RESPONSE_FAILURE)
    data = json.loads(data)
    return HttpResponse(stations.register(data))

@require_http_methods(["POST"])
@login_required
def station_registration_resolve(request):
    stations.registration_resolve(request.POST.get('network_id', ''), request.POST.get('approve', None) == 'True')
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

@require_http_methods(["POST"])
@csrf_exempt
def station_data(request):
    data = request.POST.get('json', None)
    if data == None: return HttpResponse(RESPONSE_FAILURE)
    data = json.loads(data)
    if stations.new_data(data):
        return HttpResponse(RESPONSE_SUCCESS)
    else:
        return HttpResponse(RESPONSE_FAILURE)

@require_http_methods(["POST"])
@csrf_exempt
def station_version(request):
    return HttpResponse(stations.get_version())

@require_http_methods(["GET", "POST"])
@csrf_exempt
def station_code_download(request):
    filepath = stations.get_code_filepath()
    with open(filepath, 'rb') as zipfile:
        wrapper = FileWrapper(zipfile)
        response = HttpResponse(wrapper, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename=station_code.zip'
        response['Content-Length'] = path.getsize(filepath)
        return response

@require_http_methods(["POST"])
@login_required
def station_error_resolve(request):
    stations.error_resolve(request.POST.get('id', ''))
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
    graph = PIL.Image.open(stations.get_graph_path(graph))
    graph.save(response, 'PNG')
    return response

@require_http_methods(["POST"])
@login_required
def warning_delete(request):
    if stations.warning_delete(int(request.POST.get('id', '-1'))):
        messages.add_message(request, messages.SUCCESS, "Warning deleted")
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

@require_http_methods(["POST"])
@login_required
def warning_add(request):
    expression = request.POST.get('expression', '')
    message = request.POST.get('message', '')
    if stations.warning_add(expression, message):
        messages.add_message(request, messages.SUCCESS, "Warning added")
    else:
        messages.add_message(request, messages.ERROR, "Invalid warning")
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
