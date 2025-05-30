from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from vacancies.models import Vacancy
from contacts.models import Contact, ContactPhone
from contacts.utils import normalize_phone_number
import requests
from bs4 import BeautifulSoup
import re
import time

class Command(BaseCommand):
    help = 'Parse contact name and phone from active and new Work.ua vacancies'

    def handle(self, *args, **kwargs):
        # Step 1: Select vacancies with work_id, is_active=True, is_new=True, and link
        vacancies = Vacancy.objects.filter(
            work_id__isnull=False,
            is_active=True,
            is_new=True,
            link__isnull=False
        )
        self.stdout.write(self.style.SUCCESS(f'Found {vacancies.count()} vacancies to process.'))

        if not vacancies:
            self.stdout.write(self.style.WARNING('No vacancies found matching criteria.'))
            return

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Referer': 'https://www.work.ua/',
            'DNT': '1',
            'Connection': 'keep-alive',
        }
        cookies = {
            'ss': '1',
            'region': '0',
        }

        for vacancy in vacancies:
            self.stdout.write(self.style.NOTICE(f'Processing vacancy: {vacancy.title} (Work ID: {vacancy.work_id})'))
            try:
                # Step 2: Fetch vacancy page
                response = requests.get(vacancy.link, headers=headers, cookies=cookies, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')

                # Find contact block
                contact_block = soup.find('ul', class_='list-unstyled sm:mt-2xl mt-lg mb-0')
                if not contact_block:
                    self.stdout.write(self.style.WARNING(f'No contact block found for vacancy {vacancy.title}.'))
                    continue

                # Find the <li> with phone icon
                contact_name = None
                phone_number = None

                # Search for <li> containing <span class="glyphicon glyphicon-phone">
                contact_li = None
                for li in contact_block.find_all('li', class_='text-indent no-style mt-sm mb-0'):
                    if li.find('span', class_='glyphicon glyphicon-phone'):
                        contact_li = li
                        break

                if contact_li:
                    # Extract name from <span class="mr-sm"> within this <li>
                    name_span = contact_li.find('span', class_='mr-sm')
                    contact_name = name_span.text.strip() if name_span else None
                    self.stdout.write(self.style.NOTICE(f'Found name span: {contact_name}'))

                    # Extract phone
                    phone_block = contact_li.find('span', id='contact-phone')
                    if phone_block:
                        phone_link = phone_block.find('a', class_='js-get-phone sendr hidden')
                        if phone_link:
                            phone_text = phone_link.text.strip()
                            phone_number = normalize_phone_number(phone_text)
                            self.stdout.write(self.style.NOTICE(f'Found phone: {phone_text}, normalized: {phone_number}'))
                        else:
                            self.stdout.write(self.style.WARNING(f'No phone number found in contact block for vacancy {vacancy.title}.'))
                    else:
                        self.stdout.write(self.style.WARNING(f'No phone block found for vacancy {vacancy.title}.'))
                else:
                    self.stdout.write(self.style.WARNING(f'No contact <li> with phone icon found for vacancy {vacancy.title}.'))

                self.stdout.write(self.style.NOTICE(
                    f'Parsed: name={contact_name}, phone={phone_number}'
                ))

                if not phone_number or not contact_name:
                    self.stdout.write(self.style.WARNING(f'Skipping vacancy {vacancy.title}: Missing name or valid phone.'))
                    continue

                # Step 3: Process contact and phone
                contact_phone = ContactPhone.objects.filter(phone=phone_number).first()
                if contact_phone:
                    # Phone found, update contact
                    contact = contact_phone.contact
                    self.stdout.write(self.style.NOTICE(f'Found existing contact: {contact}'))

                    if not contact.company:
                        # No company, set vacancy's company
                        contact.company = vacancy.company
                        contact.save()
                        self.stdout.write(self.style.SUCCESS(f'Set company {vacancy.company} for contact {contact}.'))
                    elif contact.company != vacancy.company:
                        # Different company, set as another_company
                        contact.another_company = vacancy.company
                        contact.save()
                        self.stdout.write(self.style.SUCCESS(f'Set another_company {vacancy.company} for contact {contact}.'))
                    else:
                        self.stdout.write(self.style.NOTICE(f'Contact {contact} already has matching company {vacancy.company}.'))
                else:
                    # No phone found, create new contact and phone
                    contact = Contact.objects.create(
                        first_name=contact_name,
                        company=vacancy.company,
                        is_active=False
                    )
                    ContactPhone.objects.create(
                        contact=contact,
                        phone=phone_number,
                        name='Основний'
                    )
                    self.stdout.write(self.style.SUCCESS(f'Created new contact: {contact} with phone {phone_number}.'))

            except requests.RequestException as e:
                self.stdout.write(self.style.ERROR(f'Error fetching {vacancy.link}: {e}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Unexpected error for vacancy {vacancy.title}: {e}'))
                import traceback
                self.stdout.write(self.style.ERROR(traceback.format_exc()))

            # Delay to avoid overwhelming the server
            time.sleep(1)