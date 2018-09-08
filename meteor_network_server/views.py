from django.http import Http404, HttpResponse
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.contrib import messages
from wsgiref.util import FileWrapper
from datetime import datetime
import json
import math
from os import path

from .stations.models import *
from .stations import stations

RESPONSE_SUCCESS = "success"
RESPONSE_FAILURE = "failure"
STATIONS_PER_ROW = 5

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

@require_http_methods(["GET"])
def index(request):
    station_list = stations.get_current_list()

    station_rows = []
    for i in range(0, len(station_list), STATIONS_PER_ROW):
        row = []
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
            elif (timezone.now() - station.last_updated).total_seconds() // 3600 > 12:
                status_text = "Not connecting"
                status_color = 'orange'
            elif (timezone.now() - station.last_updated).total_seconds() // 3600 > 72:
                status_text = "Disconnected"
                status_color = 'black'
            else:
                status_text = "Good"
                status_color = 'green'

            station_card['status_text'] = status_text
            station_card['status_color'] = status_color

            row.append(station_card)

        station_rows.append(row)

    context = { 'station_rows' : station_rows, 'settings' : settings }
    return render(request, 'index.html', context)

@require_http_methods(["GET"])
def station_view(request, network_id):
    context = { 'station' : get_object_or_404(Station, network_id=network_id), 'settings' : settings }
    return render(request, 'station.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def station_register(request):
    return HttpResponse(stations.register(request.POST))

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
