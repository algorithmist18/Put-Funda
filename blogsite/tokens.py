# Importing libraries
from django.contrib.auth.tokens import PasswordResetTokenGenerator

class AccountActivationTokenGen(PasswordResetTokenGenerator):

	def _make_hash_value(self, user, timestamp):

		return (

			str(user.pk) +
			str(timestamp) +
			str(user.profile.email_confirmed)
		)


class PasswordResetToken(PasswordResetTokenGenerator):

	def _make_hash_value(self, user, timestamp):

		return (

			str(user.pk) +
			str(timestamp) +
			str(user.username)
		)

account_activation_token = AccountActivationTokenGen() 
password_reset_token = PasswordResetToken() 