from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from vacancies.models import Vacancy
from companies.models import Company
import requests
from bs4 import BeautifulSoup
import re
import time

class Command(BaseCommand):
    help = 'Parse vacancies from Work.ua'

    def handle(self, *args, **kwargs):
        # Step 1: Mark all existing vacancies with work_id as inactive and not new
        updated_count = Vacancy.objects.filter(work_id__isnull=False).update(
            is_active=False,
            is_new=False
        )
        self.stdout.write(self.style.SUCCESS(f'Marked {updated_count} existing vacancies as inactive and not new.'))

        # Step 2: Scrape vacancies from Work.ua
        url = 'https://www.work.ua/jobs/'
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
        params = {
            'ss': '1',
            'region': '0',
        }
        try:
            page = 1
            max_pages = 10000
            while page <= max_pages:
                params['page'] = page
                self.stdout.write(self.style.NOTICE(f'Fetching URL: {url} page {page}'))
                response = requests.get(url, headers=headers, cookies=cookies, params=params, timeout=10)
                response.raise_for_status()
                self.stdout.write(self.style.SUCCESS(
                    f'Successfully fetched page {page}. Status code: {response.status_code}'))

                soup = BeautifulSoup(response.text, 'html.parser')
                vacancy_cards = soup.find_all('div', class_='job-link')

                if not vacancy_cards:
                    self.stdout.write(self.style.WARNING(
                        f'No vacancy cards found on page {page}. Stopping.'))
                    break

                self.stdout.write(self.style.NOTICE(
                    f'Found {len(vacancy_cards)} vacancy cards on page {page}.'))

                for card in vacancy_cards:
                    # Extract title and work_id
                    title_tag = card.find('h2', class_='my-0')
                    if not title_tag or not title_tag.find('a'):
                        self.stdout.write(self.style.WARNING('Skipping card: No title or link found.'))
                        continue
                    title = title_tag.find('a').text.strip()
                    href = title_tag.find('a')['href']
                    link = f"https://www.work.ua{href}" if href.startswith('/') else href
                    work_id_match = re.search(r'/jobs/(\d+)/', href)
                    if not work_id_match:
                        self.stdout.write(self.style.WARNING(f'Skipping card: No work_id found in href {href}.'))
                        continue
                    work_id = work_id_match.group(1)

                    # Extract company name from mt-xs block
                    company_name = None
                    company_tag_block = card.find('div', class_='mt-xs')
                    if company_tag_block:
                        company_tag = company_tag_block.find('span', class_='strong-600')
                        company_name = company_tag.text.strip() if company_tag else None

                    # Extract company_id
                    logo_img = card.find('img', class_='preview-img-logo')
                    company_id = None
                    if logo_img and logo_img['src']:
                        company_id_match = re.search(r'/(\d+)_company_logo', logo_img['src'])
                        company_id = company_id_match.group(1) if company_id_match else None

                    # Extract status
                    status_tag = card.find('span', class_='label-orange-light')
                    status = 'hot' if status_tag and 'Гаряча' in status_tag.text else 'standard'

                    # Extract city
                    city = None
                    if company_tag_block:
                        for span in company_tag_block.find_all('span'):
                            classes = span.get('class', [])
                            if classes:
                                # skip spans that have any class specified
                                continue
                            city_text = span.get_text(strip=True)
                            if city_text and 'км' not in city_text:
                                city = city_text.rstrip(',').strip()
                                break

                    self.stdout.write(
                        self.style.NOTICE(
                            f'Parsed: title={title}, work_id={work_id}, company_id={company_id}, '
                            f'company_name={company_name}, status={status}, city={city}, link={link}'
                        )
                    )

                    # Step 3: Handle company
                    company = None
                    if company_id and company_name:
                        company, created = Company.objects.get_or_create(
                            work_id=company_id,
                            defaults={
                                'name': company_name,
                                'is_active': False,
                                'responsible': None
                            }
                        )
                        if not created and company.name != company_name:
                            company.name = company_name
                            company.save()
                        self.stdout.write(self.style.SUCCESS(
                            f'{"Created" if created else "Found"} company: {company_name} (Work ID: {company_id})'
                        ))
                    else:
                        self.stdout.write(self.style.WARNING(f'Skipping vacancy {title}: Missing company data.'))
                        continue

                    # Step 4: Handle vacancy
                    vacancy, created = Vacancy.objects.get_or_create(
                        work_id=work_id,
                        defaults={
                            'title': title,
                            'company': company,
                            'city': city,
                            'link': link,
                            'is_active': True,
                            'is_new': True,
                            'status': status
                        }
                    )
                    if not created:
                        vacancy.title = title
                        vacancy.company = company
                        vacancy.city = city
                        vacancy.link = link
                        vacancy.is_active = True
                        vacancy.is_new = False
                        vacancy.status = status
                        vacancy.save()
                    self.stdout.write(self.style.SUCCESS(
                        f'{"Created" if created else "Updated"} vacancy: {title} (Work ID: {work_id})'
                    ))
                    time.sleep(0.1)
                page += 1

        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f'Error fetching Work.ua: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Unexpected error: {e}'))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))