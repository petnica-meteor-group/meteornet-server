from django.http import Http404, HttpResponse
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.contrib import messages

import json
import math

from .telemetry import stations

STATION_PARAM_ID = "id"
STATION_PARAM_DATA = "data"
STATION_PARAM_ERROR = "error"

RESPONSE_SUCCESS = "success"
RESPONSE_FAILTURE = "failure"

@require_http_methods(["POST"])
def login(request):
    username = request.POST['username']
    password = request.POST['password']
    user = authenticate(request, username=username, password=password)
    if user is not None:
        django_login(request, user)
        return redirect('/')
    else:
        messages.add_message(request, messages.ERROR, "Wrong credentials")
        return redirect('/')

@require_http_methods(["POST"])
def logout(request):
    django_logout(request)
    return redirect('/')

def format_last_updated(station):
    minutes = int((timezone.now() - station.last_updated).total_seconds() // 60)

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
    for i in range(0, len(station_list), 2):
        row = []

        station = station_list[i]
        error_reported = len(stations.get_errors(station.id)) > 0
        row.append((station, format_last_updated(station), error_reported))
        if i < len(station_list) - 1:
            station = station_list[i + 1]
            error_reported = len(stations.get_errors(station.id)) > 0
            row.append((station, format_last_updated(station), error_reported))

        station_rows.append(row)

    context = { 'station_rows' : station_rows, 'settings' : settings }
    return render(request, 'index.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def station_register(request):
    if not STATION_PARAM_DATA in request.POST:
        return HttpResponse(RESPONSE_FAILTURE)

    data = json.loads(request.POST[STATION_PARAM_DATA])

    id = stations.register(data)

    return HttpResponse(id)

@csrf_exempt
@require_http_methods(["POST"])
def station_update(request):
    if (not STATION_PARAM_ID in request.POST) or (not STATION_PARAM_DATA in request.POST):
        return HttpResponse(RESPONSE_FAILTURE)

    id = request.POST[STATION_PARAM_ID]
    data = json.loads(request.POST[STATION_PARAM_DATA])

    if stations.update(id, data):
        return HttpResponse(RESPONSE_SUCCESS)
    else:
        return HttpResponse(RESPONSE_FAILIURE)

@csrf_exempt
@require_http_methods(["POST"])
def station_error(request):
    if (not STATION_PARAM_ID in request.POST) or (not STATION_PARAM_ERROR in request.POST):
        return HttpResponse(RESPONSE_FAILTURE)

    id = request.POST[STATION_PARAM_ID]
    error = request.POST[STATION_PARAM_ERROR]

    if stations.error(id, error):
        return HttpResponse(RESPONSE_SUCCESS)
    else:
        return HttpResponse(RESPONSE_FAILIURE)
