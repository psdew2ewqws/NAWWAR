"""
User views for template-based pages.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from apps.users import services, selectors
from apps.users.forms import LoginForm, RegisterForm, ProfileUpdateForm


def home_view(request):
    """Home page — The Reveal."""
    return render(request, 'home.html')


def login_view(request):
    """Login page view."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = LoginForm()

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            user = authenticate(request, username=email, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.full_name or user.email}!')
                next_url = request.GET.get('next', 'dashboard')
                return redirect(next_url)
            else:
                form.add_error(None, 'Invalid email or password.')

    return render(request, 'registration/login.html', {'form': form})


def register_view(request):
    """Registration page view."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = RegisterForm()

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                user = services.user_create(
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data.get('first_name', ''),
                    last_name=form.cleaned_data.get('last_name', ''),
                )
                login(request, user)
                messages.success(request, 'Welcome! Your account has been created successfully.')
                return redirect('dashboard')
            except Exception as e:
                form.add_error(None, str(e))

    return render(request, 'registration/register.html', {'form': form})


def logout_view(request):
    """Logout view."""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('home')


@login_required
def dashboard_view(request):
    """User dashboard view."""
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES)
        if form.is_valid():
            data = {
                'first_name': form.cleaned_data.get('first_name'),
                'last_name': form.cleaned_data.get('last_name'),
                'phone': form.cleaned_data.get('phone'),
            }

            # Handle avatar upload
            if form.cleaned_data.get('avatar'):
                data['avatar'] = form.cleaned_data['avatar']

            # Remove None values
            data = {k: v for k, v in data.items() if v is not None}

            services.user_update(user=request.user, data=data)
            messages.success(request, 'Profile updated successfully!')
            return redirect('dashboard')

    return render(request, 'dashboard.html')


@login_required
def user_list_view(request):
    """User list view."""
    users = selectors.user_list()
    return render(request, 'users/user_list.html', {'users': users})
