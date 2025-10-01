import time
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = 'Espera a que la base de datos esté disponible'

    def add_arguments(self, parser):
        parser.add_argument(
            '--timeout',
            type=int,
            default=60,
            help='Tiempo máximo de espera en segundos (default: 60)'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=2,
            help='Intervalo entre intentos en segundos (default: 2)'
        )

    def handle(self, *args, **options):
        timeout = options['timeout']
        interval = options['interval']
        
        self.stdout.write('⏳ Esperando a que la base de datos esté disponible...')
        
        start_time = time.time()
        
        while True:
            try:
                # Intentar conectar a la base de datos por defecto
                db_conn = connections['default']
                db_conn.cursor()
                break
            except OperationalError:
                elapsed_time = time.time() - start_time
                
                if elapsed_time >= timeout:
                    self.stdout.write(
                        self.style.ERROR(
                            f'❌ Timeout: La base de datos no estuvo disponible después de {timeout} segundos'
                        )
                    )
                    raise
                
                self.stdout.write(
                    f'🔄 Base de datos no disponible, reintentando en {interval} segundos... '
                    f'(transcurridos: {int(elapsed_time)}s)'
                )
                time.sleep(interval)
        
        self.stdout.write(
            self.style.SUCCESS('✅ Base de datos disponible!')
        )