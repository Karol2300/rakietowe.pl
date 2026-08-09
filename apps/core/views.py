from django.http import HttpResponse


def home(request):
    return HttpResponse("Racket Sports Shop - scaffold running.")
