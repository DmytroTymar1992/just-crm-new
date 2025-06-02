from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from contacts.models import Contact
from .forms import ContactForm, ContactPhoneFormSet, ContactEmailFormSet
from companies.models import Company
from chats.models import Interaction
from main.pagination_utils import get_paginated_objects
from django.db.models import Q


@login_required
def contact_list(request):
    # Отримуємо пошуковий запит
    search_query = request.GET.get('q', '').strip()

    # Базовий queryset
    contacts = Contact.objects.all()

    # Фільтруємо за пошуковим запитом
    if search_query:
        contacts = contacts.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(company__name__icontains=search_query) |
            Q(phones__phone__icontains=search_query) |
            Q(phones__telegram_username__icontains=search_query) |
            Q(phones__telegram_id__icontains=search_query) |
            Q(emails__email__icontains=search_query)
        ).distinct()

    # Пагінація
    paginated_contacts = get_paginated_objects(request, contacts, 24)

    # Якщо це AJAX-запит, повертаємо лише таблицю та пагінацію
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'contacts/contact_list_table.html', {'contacts': paginated_contacts})

    return render(request, 'contacts/contact_list.html', {'contacts': paginated_contacts})


@login_required
def contact_create(request):
    company_id = request.GET.get('company_id')
    initial = {}
    if company_id:
        initial['company'] = get_object_or_404(Company, pk=company_id)

    if request.method == 'POST':
        form = ContactForm(request.POST, request.FILES, initial=initial)
        phone_formset = ContactPhoneFormSet(request.POST, prefix='phones')
        email_formset = ContactEmailFormSet(request.POST, prefix='emails')
        if form.is_valid() and phone_formset.is_valid() and email_formset.is_valid():
            contact = form.save()
            for phone_form in phone_formset:
                if phone_form.cleaned_data and not phone_form.cleaned_data.get('DELETE', False):
                    phone = phone_form.save(commit=False)
                    phone.contact = contact
                    phone.save()
            for email_form in email_formset:
                if email_form.cleaned_data and not email_form.cleaned_data.get('DELETE', False):
                    email = email_form.save(commit=False)
                    email.contact = contact
                    email.save()
            return redirect('contact_detail', pk=contact.pk)
    else:
        form = ContactForm(initial=initial)
        phone_formset = ContactPhoneFormSet(prefix='phones')
        email_formset = ContactEmailFormSet(prefix='emails')
    return render(request, 'contacts/contact_create.html', {
        'form': form,
        'phone_formset': phone_formset,
        'email_formset': email_formset,
        'company_id': company_id
    })

@login_required
def contact_detail(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    interactions = Interaction.objects.filter(contact=contact).order_by('date')
    return render(request, 'contacts/contact_detail.html', {
        'contact': contact,
        'interactions': interactions
    })