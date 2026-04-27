from django.shortcuts import render

import logging

logger = logging.getLogger(__name__)

# Summary: Содержит логику для home.
def home(request):
    return render(request, "public/home.html")

# Summary: Содержит логику для access denied.
def access_denied(request):
    return render(request, "public/access_denied.html", status=403)
