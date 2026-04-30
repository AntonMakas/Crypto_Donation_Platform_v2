"""
Signals for the jars app.

Jar cache invalidation after donation verification is handled in
apps.donations.signals.refresh_jar_on_donation_verified, which calls
jar.refresh_cached_totals() and jar.sync_status() whenever a Donation's
is_verified field transitions False → True.

Keeping the handler in the donations app avoids registering duplicate
post_save receivers on donations.Donation from two separate apps.
"""
