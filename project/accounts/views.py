"""
Class based views.

This module will include views for the accounts app.
"""

from accounts.authentication import send_activation_email
from accounts.forms import ProfileEditForm, UserRegistrationForm
from accounts.models import Profile
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic.edit import FormView, UpdateView


class ProfileFollow(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # Prevent users from following themselves.
        if request.user.username == kwargs["username"]:
            pass
        else:
            following_profile = Profile.objects.get(user__username=kwargs["username"])

            self.request.user.profile.following.add(following_profile)

        redirect_to = reverse("profile", kwargs={"username": kwargs["username"]})

        return HttpResponseRedirect(redirect_to)


class ProfileUnfollow(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # Prevent users from following themselves.
        if request.user.username == kwargs["username"]:
            pass
        else:
            following_profile = Profile.objects.get(user__username=kwargs["username"])

            self.request.user.profile.following.remove(following_profile)

        redirect_to = reverse("profile", kwargs={"username": kwargs["username"]})

        return HttpResponseRedirect(redirect_to)


class RegisterView(FormView):
    """
    A form view that handles user registration.
    """

    template_name = "accounts/register/register.html"
    form_class = UserRegistrationForm
    success_url = "/"

    def _create_user(self, form):
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]
        email = form.cleaned_data["email"]
        user = get_user_model().objects.create_user(username, email, password)
        return user

    def _send_email(self, user):
        domain = get_current_site(self.request).domain
        send_activation_email(user, domain)

    def _login(self, user):
        login(self.request, user)

    def form_valid(self, form):
        user = self._create_user(form)

        self._send_email(user)
        self._login(user)

        return super(RegisterView, self).form_valid(form)


class PasswordResetView(auth_views.PasswordResetView):
    template_name = "accounts/users/password_reset.html"
    email_template_name = "accounts/users/password_reset_email.html"
    subject_template_name = "accounts/users/password_reset_subject.txt"
    from_email = settings.EMAIL_HOST_USER
    success_url = reverse_lazy("accounts_password_reset_done")


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "accounts/users/password_reset_done.html"


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "accounts/users/password_reset_confirm.html"
    success_url = reverse_lazy("accounts_password_reset_complete")


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "accounts/users/password_reset_complete.html"


class SettingsView(LoginRequiredMixin, UpdateView):
    """A form view to edit Profile"""

    login_url = "accounts_login"
    form_class = ProfileEditForm
    success_url = reverse_lazy("accounts_settings")
    template_name = "accounts/settings.html"

    def get_object(self, queryset=None):
        return Profile.objects.get(user=self.request.user)

    def get_initial(self):
        profile = Profile.objects.get(user=self.request.user)
        self.initial.update(
            {
                "username": profile.user.username,
                "email": profile.user.email,
                "first_name": profile.first_name or None,
                "last_name": profile.last_name or None,
                "about_me": profile.about_me or None,
                "profile_image": profile.profile_image or None,
            }
        )
        return super(SettingsView, self).get_initial()


class UserProfileView(LoginRequiredMixin, View):
    """A view that shows profile for authorized users"""

    def get(self, request, username=None):
        profile = get_object_or_404(Profile, user__username=username)

        return TemplateResponse(
            request,
            "account.html",
            {
                "profile": profile,
            },
        )


@login_required
def expunge_user(request):
    """
    Delete User Information
    """

    user_model = get_user_model()
    user = get_object_or_404(user_model, username=request.user.username)

    profile = get_object_or_404(Profile, user=user)

    # Expunge personally identifiable data in user
    expunged_user_data = {
        "is_active": False,
        "email": "",
        "first_name": "",
        "last_name": "",
        "username": f"expunged-{ user.id }",
    }
    user.__dict__.update(expunged_user_data)
    user.save()

    # Expunge personally identifiable data in profile
    expunged_profile_data = {
        "first_name": "",
        "last_name": "",
        "about_me": "",
    }
    profile.__dict__.update(expunged_profile_data)
    profile.save()

    return redirect("/")
