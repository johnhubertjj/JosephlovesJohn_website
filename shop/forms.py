"""Forms used by the shop checkout and account flows."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


class CheckoutForm(forms.Form):
    """Collect customer details for the portfolio checkout flow."""

    full_name = forms.CharField(max_length=180)
    email = forms.EmailField()
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    save_details = forms.BooleanField(required=False)


class ShopAuthenticationForm(AuthenticationForm):
    """Apply site-specific presentation hooks to the login form."""

    username = forms.CharField(widget=forms.TextInput(attrs={"autofocus": True}))


class RegisterForm(UserCreationForm):
    """Create a storefront account for returning listeners."""

    email = forms.EmailField()
    full_name = forms.CharField(max_length=180)

    class Meta(UserCreationForm.Meta):
        """Registration fields shown to the shopper."""

        model = User
        fields = ("username", "email", "full_name")
