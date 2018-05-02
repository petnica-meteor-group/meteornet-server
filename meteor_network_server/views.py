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

from .telemetry import station

STATION_PARAM_ID = "id"
STATION_PARAM_DATA = "data"

RESPONSE_SUCCESS = "success"
RESPONSE_FAILTURE = "failure"

def format_last_updated(station):
    minutes = int((timezone.now() - station['last_updated']).total_seconds() // 60)

    if minutes > 1:
        return str(minutes) + " minutes ago."
    elif minutes == 1:
        return str(minutes) + " minute ago."
    else:
        return "Less than a minute ago."

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

@require_http_methods(["GET"])
def index(request):
    stations = station.get_current_list()

    station_rows = []
    for i in range(0, len(stations), 2):
        row = []

        row.append((stations[i], format_last_updated(stations[i])))
        if i < len(stations) - 1:
            row.append((stations[i + 1], format_last_updated(stations[i + 1])))

        station_rows.append(row)

    context = { 'station_rows' : station_rows }
    return render(request, 'index.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def station_register(request):
    data = json.loads(request.POST[STATION_PARAM_DATA])

    id = station.create(data)

    return HttpResponse(id)

@csrf_exempt
@require_http_methods(["POST"])
def station_update(request):
    id = request.POST[STATION_PARAM_ID]
    data = json.loads(request.POST[STATION_PARAM_DATA])

    station = station.get(id)
    if station == None:
        return HttpResponse(RESPONSE_FAILTURE)

    station.update(id, data)

    return HttpResponse(RESPONSE_SUCCESS)
