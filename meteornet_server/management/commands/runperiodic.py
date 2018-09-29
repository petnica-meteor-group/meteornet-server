from django.core.management.base import BaseCommand, CommandError
import threading
import signal
from ...stations import stations

class Command(BaseCommand):
    help = 'Keep periodic operations running'

    def update_statuses(self):
        with self.lock:
            while True:
                stations.update_statuses()
                if self.done: break
                self.condition.wait(timeout=900)

    def delete_old_data(self):
        with self.lock:
            while True:
                self.condition.wait(timeout=86400)
                if self.done: break
                stations.delete_old_data()

    def handle(self, *args, **options):
        self.done = False
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        update_statuses_thread = threading.Thread(target=Command.update_statuses, args=(self,))
        update_statuses_thread.start()
        delete_old_data_thread = threading.Thread(target=Command.delete_old_data, args=(self,))
        delete_old_data_thread.start()

        try:
            signal.signal(signal.SIGINT, lambda *args: None)
            signal.pause()
        except KeyboardInterrupt:
            pass

        with self.lock:
            self.done = True
            self.condition.notify_all()
        update_statuses_thread.join()
        delete_old_data_thread.join()
