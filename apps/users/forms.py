"""
User forms for template-based views.
"""
from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class LoginForm(forms.Form):
    """Form for user login."""

    email = forms.EmailField(
        max_length=255,
        widget=forms.EmailInput(attrs={
            'placeholder': 'you@example.com',
            'autocomplete': 'email',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'autocomplete': 'current-password',
        })
    )


class RegisterForm(forms.Form):
    """Form for user registration."""

    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'John',
            'autocomplete': 'given-name',
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Doe',
            'autocomplete': 'family-name',
        })
    )
    email = forms.EmailField(
        max_length=255,
        widget=forms.EmailInput(attrs={
            'placeholder': 'you@example.com',
            'autocomplete': 'email',
        })
    )
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'autocomplete': 'new-password',
        })
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'autocomplete': 'new-password',
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'Passwords do not match.')

        return cleaned_data


class ProfileUpdateForm(forms.Form):
    """Form for updating user profile."""

    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    phone = forms.CharField(max_length=20, required=False)
    avatar = forms.ImageField(required=False)
