from django.core.management.base import BaseCommand
from core.models import User


class Command(BaseCommand):
    help = 'Fix existing superusers by assigning them ADMIN role'

    def handle(self, *args, **options):
        # Get all superusers
        superusers = User.objects.filter(is_superuser=True)
        
        if not superusers.exists():
            self.stdout.write(self.style.WARNING('No superusers found in the database.'))
            return
        
        updated_count = 0
        for user in superusers:
            if user.role != User.Role.ADMIN:
                old_role = user.get_role_display()
                user.role = User.Role.ADMIN
                user.save()
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Updated {user.username}: {old_role} → Administrator'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ {user.username} already has Administrator role'
                    )
                )
        
        if updated_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully updated {updated_count} superuser(s) to ADMIN role'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    '\nAll superusers already have the correct ADMIN role'
                )
            )
