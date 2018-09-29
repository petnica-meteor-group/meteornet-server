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
    path('administration_notes_update', views.administration_notes_update, name='administration_notes_update'),
    path('station_view/<network_id>', views.station_view, name='station_view'),
    path('station_register', views.station_register, name='station_register'),
    path('station_registration_resolve', views.station_registration_resolve, name='station_registration_resolve'),
    path('station_data', views.station_data, name='station_data'),
    path('station_version', views.station_version, name='station_version'),
    path('station_code_download', views.station_code_download, name='station_code_download'),
    path('station_error_resolve', views.station_error_resolve, name='station_error_resolve'),
    path('station_delete', views.station_delete, name='station_delete'),
    path('station_graph/<graph>', views.station_graph, name='station_graph'),
    path('rule_delete', views.rule_delete, name='rule_delete'),
    path('rule_add', views.rule_add, name='rule_add'),
]
