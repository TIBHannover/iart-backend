from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

class Collection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    hash_id = models.CharField(max_length=256)
    name = models.CharField(max_length=256)
    visibility = models.CharField(max_length=2, choices=[("V", "Visible"), ("A", "Authenticated"), ("U", "User")], default="U")
    status = models.CharField(max_length=2, choices=[("U", "Upload"), ("R", "Ready")], default="U")
    progress = models.FloatField(default=0.0)

class Image(models.Model):
    hash_id = models.CharField(max_length=256)


class ImageUserRelation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    image = models.ForeignKey(Image, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    # TODO on delete
    library = models.BooleanField(default=False)

    def __str__(self):
        return "{} {}, {}".format(self.user, self.image.hash_id)


class ImageUserTag(models.Model):
    name = models.CharField(max_length=256)
    ImageUserRelation = models.ForeignKey(ImageUserRelation, on_delete=models.CASCADE)
