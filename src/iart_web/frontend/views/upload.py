from django.views import View
from django.http import HttpResponse, JsonResponse
from django.conf import settings


class Upload(View):
    def get(self, request):
        # <view logic>
        return HttpResponse("result")
