# sales/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from contacts.models import Company
from .forms import CompanyForm

@login_required
def company_list(request):
    companies = Company.objects.all()
    return render(request, 'companies/company_list.html', {'companies': companies})

@login_required
def company_create(request):
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            company = form.save(commit=False)
            company.responsible = request.user
            company.save()
            return redirect('company_detail', pk=company.pk)
    else:
        form = CompanyForm()
    return render(request, 'companies/company_create.html', {'form': form})

@login_required
def company_detail(request, pk):
    company = get_object_or_404(Company, pk=pk)  # Використання pk замість slug
    contacts = company.contacts.all()
    return render(request, 'companies/company_detail.html', {'company': company, 'contacts': contacts})