import os
import json
from django.core.management.base import BaseCommand, CommandError
import pathlib
from django.contrib import auth


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        username = input("username: ")
        password = input("password: ")
        email = input("email: ")

        print(f"{username} {password}")

        if auth.models.User.objects.filter(username=username).count() > 0:
            self.stdout.write(self.style.ERROR(f"User with name {username} exists"))

        user = auth.models.User.objects.create_user(username, email, password)
        user.save()

        self.stdout.write(self.style.SUCCESS(f"User with id {user.id} created"))
