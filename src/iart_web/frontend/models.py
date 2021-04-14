from django.db import models
from django.contrib.auth.models import User
from django.conf import settings


class Image(models.Model):
    hash_id = models.CharField(max_length=256)
    width = models.IntegerField()
    height = models.IntegerField()
    visible = models.CharField(max_length=2, choices=[("V", "Visible"), ("U", "User")], default="U")

    def url_original(self):
        return settings.MEDIA_URL + self.hash_id[0:2] + "/" + self.hash_id[2:4] + "/" + self.hash_id + ".jpg"

    def url_thumbnail(self):
        return settings.MEDIA_URL + self.hash_id[0:2] + "/" + self.hash_id[2:4] + "/" + self.hash_id + "_200.jpg"


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


class Collection(models.Model):
    hash_id = models.CharField(max_length=256)
    width = models.IntegerField()
    height = models.IntegerField()
    visible = models.CharField(max_length=2, choices=[("V", "Visible"), ("U", "User")], default="U")
