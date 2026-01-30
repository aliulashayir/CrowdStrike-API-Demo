import os
from django.core.management.base import BaseCommand
from oauth2_provider.models import Application


class Command(BaseCommand):
    help = 'OAuth2 Application olusturur'

    def handle(self, *args, **options):
        client_id = "S25m2E0C0PT6SwV1qhSP69ElaaHVTXuANOFKlqDF"
        client_secret = "gxscczzJUAfAqghqmqtJeqVylnFZm3aswTqknWhd2EdV6FMJOM"

        app, created = Application.objects.get_or_create(
            client_id=client_id,
            defaults={
                'name': 'Test Client',
                'client_type': Application.CLIENT_CONFIDENTIAL,
                'authorization_grant_type': Application.GRANT_CLIENT_CREDENTIALS,
                'client_secret': client_secret
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'OAuth2 Application olusturuldu: {client_id}'))
        else:
            self.stdout.write(self.style.WARNING(f'OAuth2 Application zaten mevcut: {client_id}'))
