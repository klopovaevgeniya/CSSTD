from django.shortcuts import render

def home(request):
    return render(request, "public/home.html")

def access_denied(request):
    return render(request, "public/access_denied.html", status=403)
