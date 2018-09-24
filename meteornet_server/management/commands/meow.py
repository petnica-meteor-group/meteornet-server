from django.core.management.base import BaseCommand, CommandError
from django.core import mail

class Command(BaseCommand):
    def handle(self, *args, **options):
        mail.send_mail(
            'Test Subject',
            'Test Message.',
            'from@example.com',
            ['vladimir.nik94@gmail.com'],
            fail_silently=False,
        )
