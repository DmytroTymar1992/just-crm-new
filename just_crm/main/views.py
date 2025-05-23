# main/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def home(request):
    return render(request, 'main/home.html', {'user': request.user})
