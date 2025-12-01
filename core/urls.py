from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.views.generic import RedirectView
from . import views

app_name = 'core'

urlpatterns = [
    path('', RedirectView.as_view(url='dashboard/', permanent=False)),
    path('dashboard/', login_required(views.dashboard), name='dashboard'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='core:login'), name='logout'),
    path('profile/', login_required(views.profile), name='profile'),
    path('settings/', login_required(views.settings), name='settings'),
    path('users/create/', login_required(views.create_user), name='create_user'),
    path('users/<int:user_id>/reset-password/', login_required(views.reset_user_password), name='reset_user_password'),
]