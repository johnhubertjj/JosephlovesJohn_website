"""Forms for the main site."""

from django import forms


class ContactForm(forms.Form):
    """Capture and validate contact requests from the public site."""

    name = forms.CharField(
        max_length=120,
        widget=forms.TextInput(
            attrs={
                "id": "name",
                "autocomplete": "name",
            }
        ),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "id": "email",
                "autocomplete": "email",
                "inputmode": "email",
            }
        ),
    )
    message = forms.CharField(
        max_length=4000,
        widget=forms.Textarea(
            attrs={
                "id": "message",
                "rows": 4,
            }
        ),
    )
