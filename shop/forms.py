"""Forms used by the shop checkout and account flows."""

from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


class CheckoutConsentForm(forms.Form):
    """Collect the required acknowledgements before redirecting to Stripe."""

    accept_terms = forms.BooleanField(
        label="I have read the privacy, cookies, terms, and refunds information for this purchase."
    )


class ShopAuthenticationForm(AuthenticationForm):
    """Apply site-specific presentation hooks to the login form."""

    error_messages = {
        **AuthenticationForm.error_messages,
        "unknown_username": "That username or email is not recognised.",
        "incorrect_password": "That password is incorrect.",
    }
    username = forms.CharField(label="Username or email", widget=forms.TextInput(attrs={"autofocus": True}))

    def _resolve_login_user(self, identifier):
        """Return the matching user for a username-or-email login identifier."""

        user_model = get_user_model()
        normalized_identifier = (identifier or "").strip()
        if not normalized_identifier:
            return None

        if "@" in normalized_identifier:
            return user_model._default_manager.filter(email__iexact=normalized_identifier).order_by("id").first()

        try:
            return user_model._default_manager.get_by_natural_key(normalized_identifier)
        except user_model.DoesNotExist:
            return None

    def clean(self):
        """Attach login errors to the relevant field instead of the form."""

        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if not username or not password:
            return self.cleaned_data

        user = self._resolve_login_user(username)
        if user is None:
            self.add_error("username", self.error_messages["unknown_username"])
            return self.cleaned_data

        user_model = get_user_model()
        credentials = {
            user_model.USERNAME_FIELD: getattr(user, user_model.USERNAME_FIELD),
            "password": password,
        }
        self.user_cache = authenticate(self.request, **credentials)
        if self.user_cache is None:
            self.add_error("password", self.error_messages["incorrect_password"])
            return self.cleaned_data

        self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


class RegisterForm(UserCreationForm):
    """Create a storefront account for returning listeners."""

    email = forms.EmailField()
    full_name = forms.CharField(max_length=180)

    class Meta(UserCreationForm.Meta):
        """Registration fields shown to the shopper."""

        model = User
        fields = ("username", "email", "full_name")

    def clean_email(self):
        """Reject duplicate storefront email addresses to simplify recovery flows."""
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with that email address already exists.")
        return email
