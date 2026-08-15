from django import forms

from .models import JobApplication


class JobAnalysisForm(forms.Form):

    job_description = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 18,
                "placeholder": "Paste the complete job description here..."
            }
        )
    )

    source = forms.ChoiceField(
        choices=JobApplication.SOURCE_CHOICES
    )

    job_url = forms.URLField(
        required=False,
        widget=forms.URLInput(
            attrs={
                "placeholder": "https://..."
            }
        )
    )