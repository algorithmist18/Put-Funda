# Deletes guest accounts (see blogsite/guest_auth.py) older than a cutoff.
# Guest Users cascade-delete their Submissions/QOTDSubmissions/Leaderboard
# rows along with them, so this is also how that play data gets cleared
# out. Not scheduled automatically - run it by hand or wire it up to
# whatever cron/scheduler the deployment uses.
#
# Usage: python manage.py cleanup_guests [--days N] [--dry-run]

import datetime

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):

	help = 'Deletes guest accounts (and their play data) older than --days days.'

	def add_arguments(self, parser):

		parser.add_argument('--days', type = int, default = 7, help = 'Age in days before a guest account is removed (default: 7).')
		parser.add_argument('--dry-run', action = 'store_true', help = 'Report what would be deleted without deleting it.')

	def handle(self, *args, **options):

		cutoff = timezone.now() - datetime.timedelta(days = options['days'])
		guests = User.objects.filter(profile__is_guest = True, date_joined__lt = cutoff)
		count = guests.count()

		if options['dry_run']:
			self.stdout.write('Would delete {} guest account(s) older than {} day(s).'.format(count, options['days']))
			return

		guests.delete()
		self.stdout.write('Deleted {} guest account(s) older than {} day(s).'.format(count, options['days']))
