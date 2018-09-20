from django.core.management.base import BaseCommand, CommandError
from ...stations import stations
from ...stations import models

class Command(BaseCommand):
    help = 'Updates statuses of all approved stations.'

    def handle(self, *args, **options):
        for station in models.Station.objects.filter(approved=True):
            stations.update_status(station)
        self.stdout.write('Statuses updated.')
