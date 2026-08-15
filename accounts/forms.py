from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import (
    Profile,
    Experience,
    Education,
    Skill,
    LanguageEntry,
    Certification,
)


# =========================================================
# REGISTER
# =========================================================

class RegisterForm(forms.Form):

    email = forms.EmailField()

    password1 = forms.CharField(
        widget=forms.PasswordInput
    )

    password2 = forms.CharField(
        widget=forms.PasswordInput
    )

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()

        if User.objects.filter(username=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email

    def clean(self):
        cleaned_data = super().clean()

        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2:

            if password1 != password2:
                raise forms.ValidationError(
                    "Passwords do not match."
                )

            try:
                validate_password(password1)
            except ValidationError as error:
                self.add_error(
                    "password1",
                    error
                )

        return cleaned_data

    def save(self):
        email = self.cleaned_data["email"]

        user = User.objects.create_user(
            username=email,
            email=email,
            password=self.cleaned_data["password1"]
        )

        return user


# =========================================================
# PROFILE
# =========================================================

class ProfileForm(forms.ModelForm):

    class Meta:
        model = Profile

        fields = [
            "full_name",
            "city",
            "country",
            "relocation",
            "professional_summary",
        ]

        widgets = {
            "professional_summary": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "Short professional summary"
                }
            ),
        }


# =========================================================
# EXPERIENCE
# =========================================================

class ExperienceForm(forms.ModelForm):

    class Meta:
        model = Experience

        fields = [
            "job_title",
            "company",
            "location",
            "start_date",
            "end_date",
            "description",
            "technologies",
        ]

        widgets = {
            "job_title": forms.TextInput(
                attrs={
                    "placeholder": "e.g. IT Support Specialist"
                }
            ),

            "company": forms.TextInput(
                attrs={
                    "placeholder": "Company name"
                }
            ),

            "location": forms.TextInput(
                attrs={
                    "placeholder": "City, Country"
                }
            ),

            "start_date": forms.TextInput(
                attrs={
                    "placeholder": "e.g. 09/2018"
                }
            ),

            "end_date": forms.TextInput(
                attrs={
                    "placeholder": "e.g. 05/2022 or Present"
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "rows": 7,
                    "placeholder": (
                        "One responsibility per line"
                    )
                }
            ),

            "technologies": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": (
                        "One technology or tool per line"
                    )
                }
            ),
        }


# =========================================================
# EDUCATION
# =========================================================

class EducationForm(forms.ModelForm):

    class Meta:
        model = Education

        fields = [
            "degree",
            "institution",
            "location",
            "start_date",
            "end_date",
            "details",
        ]

        widgets = {
            "degree": forms.TextInput(
                attrs={
                    "placeholder": "e.g. B.Sc. Computer Science"
                }
            ),

            "institution": forms.TextInput(
                attrs={
                    "placeholder": "University or institution"
                }
            ),

            "location": forms.TextInput(
                attrs={
                    "placeholder": "City, Country"
                }
            ),

            "start_date": forms.TextInput(
                attrs={
                    "placeholder": "e.g. 09/2010"
                }
            ),

            "end_date": forms.TextInput(
                attrs={
                    "placeholder": "e.g. 02/2015"
                }
            ),

            "details": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Additional details"
                }
            ),
        }


# =========================================================
# SKILL
# =========================================================

class SkillForm(forms.ModelForm):

    class Meta:
        model = Skill

        fields = [
            "name",
            "level",
            "source",
            "do_not_claim",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "placeholder": "e.g. Windows 11"
                }
            ),
        }


# =========================================================
# LANGUAGE
# =========================================================

class LanguageEntryForm(forms.ModelForm):

    class Meta:
        model = LanguageEntry

        fields = [
            "language",
            "level",
            "original_level",
        ]

        widgets = {
            "language": forms.TextInput(
                attrs={
                    "placeholder": "e.g. German"
                }
            ),

            "original_level": forms.TextInput(
                attrs={
                    "placeholder": (
                        "e.g. B1+, Fluent, Gute Kenntnisse"
                    )
                }
            ),
        }


# =========================================================
# CERTIFICATION
# =========================================================

class CertificationForm(forms.ModelForm):

    class Meta:
        model = Certification

        fields = [
            "name",
            "issuer",
            "date",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "placeholder": "Certification name"
                }
            ),

            "issuer": forms.TextInput(
                attrs={
                    "placeholder": "Issuer"
                }
            ),

            "date": forms.TextInput(
                attrs={
                    "placeholder": "e.g. 08/2025"
                }
            ),
        }


# =========================================================
# CV UPLOAD
# =========================================================

class CVUploadForm(forms.Form):

    cv_file = forms.FileField(
        label="CV file"
    )

    def clean_cv_file(self):

        uploaded_file = self.cleaned_data["cv_file"]

        filename = uploaded_file.name.lower()

        if not (
            filename.endswith(".pdf")
            or filename.endswith(".docx")
        ):
            raise forms.ValidationError(
                "Only PDF and DOCX files are supported."
            )

        if uploaded_file.size > 5 * 1024 * 1024:
            raise forms.ValidationError(
                "The file is too large. Maximum size is 5 MB."
            )

        return uploaded_file