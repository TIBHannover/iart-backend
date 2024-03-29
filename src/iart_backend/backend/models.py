from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class CustomUser(AbstractUser):
    is_oidc = models.BooleanField(default=False)


class Collection(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    hash_id = models.CharField(max_length=256)
    name = models.CharField(max_length=256)
    visibility = models.CharField(
        max_length=2, choices=[("V", "Visible"), ("A", "Authenticated"), ("U", "User")], default="U"
    )
    status = models.CharField(max_length=2, choices=[("U", "Upload"), ("R", "Ready"), ("E", "Error")], default="U")
    progress = models.FloatField(default=0.0)
    date = models.DateTimeField(auto_now_add=True)


class Image(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.CASCADE)
    collection = models.ForeignKey(Collection, blank=True, null=True, on_delete=models.CASCADE)
    hash_id = models.CharField(max_length=256)


class UploadedImage(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=256)
    hash_id = models.CharField(max_length=256)


class ImageUserRelation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    image = models.ForeignKey(Image, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    # TODO on delete
    library = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user} {self.image.hash_id} {self.library}"


class ImageUserTag(models.Model):
    name = models.CharField(max_length=256)
    ImageUserRelation = models.ForeignKey(ImageUserRelation, on_delete=models.CASCADE)
