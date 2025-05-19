from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from contacts.models import Contact
from .forms import ContactForm, ContactPhoneFormSet, ContactEmailFormSet
from companies.models import Company


@login_required
def contact_list(request):
    contacts = Contact.objects.all()
    return render(request, 'contacts/contact_list.html', {'contacts': contacts})


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
    return render(request, 'contacts/contact_detail.html', {'contact': contact})