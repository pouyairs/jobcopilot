from django import forms

from .models import JobSearchTarget


class JobSearchTargetForm(forms.ModelForm):
    class Meta:
        model = JobSearchTarget

        fields = [
            "title",
            "location",
            "radius_km",
            "remote",
            "exclude_zeitarbeit",
            "minimum_match_score",
            "active",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": "e.g. IT Support Specialist",
                }
            ),

            "location": forms.TextInput(
                attrs={
                    "placeholder": "e.g. Germany, Berlin, Düsseldorf",
                }
            ),

            "radius_km": forms.NumberInput(
                attrs={
                    "min": 0,
                    "max": 500,
                    "step": 5,
                }
            ),

            "minimum_match_score": forms.NumberInput(
                attrs={
                    "min": 1,
                    "max": 10,
                    "step": 0.5,
                }
            ),
        }


    def clean_title(self):
        title = (
            self.cleaned_data
            .get(
                "title",
                "",
            )
            .strip()
        )

        if len(title) < 2:
            raise forms.ValidationError(
                "Please enter a valid job title."
            )

        return title


    def clean_location(self):
        location = (
            self.cleaned_data
            .get(
                "location",
                "",
            )
            .strip()
        )

        return location


    def clean_radius_km(self):
        radius = self.cleaned_data.get(
            "radius_km"
        )

        if radius is None:
            return 50

        if radius < 0:
            raise forms.ValidationError(
                "Radius cannot be negative."
            )

        if radius > 500:
            raise forms.ValidationError(
                "Radius cannot be greater than 500 km."
            )

        return radius


    def clean_minimum_match_score(self):
        score = self.cleaned_data.get(
            "minimum_match_score"
        )

        if score is None:
            return 6.0

        if score < 1:
            raise forms.ValidationError(
                "Minimum match score must be at least 1."
            )

        if score > 10:
            raise forms.ValidationError(
                "Minimum match score cannot be greater than 10."
            )

        return score