# sales/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from contacts.models import Company
from .forms import CompanyForm
from main.pagination_utils import get_paginated_objects
from vacancies.models import Vacancy
from django.http import JsonResponse
from django.db.models import Q
from chats.models import Interaction
from contacts.models import Contact
from django.template.loader import render_to_string
from django.core.paginator import Paginator


@login_required
def company_list(request):
    # Отримуємо пошуковий запит
    search_query = request.GET.get('q', '').strip()

    # Базовий queryset
    companies = Company.objects.all()

    # Фільтруємо за пошуковим запитом
    if search_query:
        companies = companies.filter(
            Q(name__icontains=search_query) |
            Q(work_id__icontains=search_query) |
            Q(rabota_id__icontains=search_query) |
            Q(just_id__icontains=search_query)
        )

    # Пагінація
    paginated_companies = get_paginated_objects(request, companies, 24)

    # Додаємо кількість активних вакансій
    for company in paginated_companies:
        company.work_vacancies = Vacancy.objects.filter(
            company=company,
            is_active=True,
            work_id__isnull=False
        ).exclude(work_id='').count()
        company.rabota_vacancies = Vacancy.objects.filter(
            company=company,
            is_active=True,
            rabota_id__isnull=False
        ).exclude(rabota_id='').count()
        company.just_vacancies = Vacancy.objects.filter(
            company=company,
            is_active=True,
            just_id__isnull=False
        ).exclude(just_id='').count()

    # Якщо це AJAX-запит, повертаємо лише таблицю та пагінацію
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'companies/company_list_table.html', {'companies': paginated_companies})

    return render(request, 'companies/company_list.html', {'companies': paginated_companies})

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
def check_company_exists(request):
    name = request.GET.get('name', '').strip()
    work_id = request.GET.get('work_id', '').strip()
    rabota_id = request.GET.get('rabota_id', '').strip()
    just_id = request.GET.get('just_id', '').strip()

    response = {
        'name': {'exists': False, 'company_name': None, 'company_id': None},
        'work_id': {'exists': False, 'company_name': None, 'company_id': None},
        'rabota_id': {'exists': False, 'company_name': None, 'company_id': None},
        'just_id': {'exists': False, 'company_name': None, 'company_id': None}
    }

    if name:
        company = Company.objects.filter(name__iexact=name).first()
        if company:
            response['name'] = {'exists': True, 'company_name': company.name, 'company_id': company.id}

    if work_id:
        company = Company.objects.filter(work_id=work_id).first()
        if company:
            response['work_id'] = {'exists': True, 'company_name': company.name, 'company_id': company.id}

    if rabota_id:
        company = Company.objects.filter(rabota_id=rabota_id).first()
        if company:
            response['rabota_id'] = {'exists': True, 'company_name': company.name, 'company_id': company.id}

    if just_id:
        company = Company.objects.filter(just_id=just_id).first()
        if company:
            response['just_id'] = {'exists': True, 'company_name': company.name, 'company_id': company.id}

    return JsonResponse(response)
@login_required
def company_detail(request, pk):
    company = get_object_or_404(Company, pk=pk)  # Використання pk замість slug
    contacts = company.contacts.all()
    return render(request, 'companies/company_detail.html', {'company': company, 'contacts': contacts})


@login_required
def contact_interactions(request, contact_id):
    if request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({'error': 'This endpoint requires AJAX'}, status=400)

    contact = get_object_or_404(Contact, pk=contact_id)
    interaction_qs = Interaction.objects.filter(contact=contact).select_related(
        'contact', 'contact_phone', 'contact_email'
    ).order_by('date')

    paginator = Paginator(interaction_qs, 20)
    page_number = request.GET.get('page', paginator.num_pages)  # Починаємо з останньої сторінки
    page_obj = paginator.get_page(page_number)
    interactions = page_obj.object_list

    html = ''
    for interaction in interactions:
        html += render_to_string(
            'chats/interaction_item.html',
            {'interaction': interaction},
            request=request
        )

    return JsonResponse({
        'contact_name': f"{contact.first_name} {contact.last_name or ''}".strip(),
        'html': html,
        'has_previous': page_obj.has_previous(),
        'page': page_obj.number,
        'previousScrollHeight': interactions.count() * 100  # Приблизне значення
    })