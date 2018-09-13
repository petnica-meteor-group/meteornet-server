"""meteor_network_telemetry URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
    path('', views.index, name='index'),
    path('stations_overview', views.stations_overview, name='stations_overview'),
    path('administration', views.administration, name='administration'),
    path('station_view/<network_id>', views.station_view, name='station_view'),
    path('station_register', views.station_register, name='station_register'),
    path('station_resolve_registration', views.station_resolve_registration, name='station_resolve_registration'),
    path('station_status', views.station_status, name='station_status'),
    path('station_version', views.station_version, name='station_version'),
    path('station_update', views.station_update, name='station_update'),
]
