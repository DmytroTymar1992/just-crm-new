# main/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate
from .models import CustomUser


class CustomLoginForm(AuthenticationForm):
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    'Логін або пароль не правильні',
                    code='invalid_login'
                )
            else:
                # Перевірка статусу користувача
                if self.user_cache.status == 'fired':
                    raise forms.ValidationError(
                        'В доступі відмовлено',  # Те саме повідомлення для безпеки
                        code='fired_user'
                    )
                elif self.user_cache.status == 'on_vacation':
                    raise forms.ValidationError(
                        'В доступі відмовлено',
                        code='on_vacation'
                    )

        return self.cleaned_data