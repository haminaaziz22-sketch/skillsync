from datetime import datetime
from django import forms
from django.utils import timezone
from django import forms
import json
from .models import Session, Skill, UserSkill, Offer, UserProfile
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User

INPUT_CLASS = (
    "w-full block rounded-xl border-2 border-gray-300 bg-white "
    "px-4 py-3 text-gray-900 placeholder-gray-400 "
    "shadow-sm outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 "
    "transition"
)

class CustomRegisterForm(UserCreationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "Choose a username",
            "autocomplete": "username",
        })
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "Enter your email",
            "autocomplete": "email",
        })
    )

    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "Create a password",
            "autocomplete": "new-password",
        })
    )

    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "Confirm password",
            "autocomplete": "new-password",
        })
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Email or Username",
        widget=forms.TextInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "Enter email or username",
            "autocomplete": "username",
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "Enter your password",
            "autocomplete": "current-password",
        })
    )
        

class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "Enter current password",
            "autocomplete": "current-password",
        })
    )

    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "Enter new password",
            "autocomplete": "new-password",
        })
    )

    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "Confirm new password",
            "autocomplete": "new-password",
        })
    )

class UserSkillForm(forms.Form):
    existing_skill = forms.ModelChoiceField(
        queryset=Skill.objects.all().order_by('name'),
        required=False,
        label="Choose a skill",
        widget=forms.Select(attrs={
            'class': 'w-full border border-gray-300 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500'
        })
    )
    new_skill = forms.CharField(
        max_length=100,
        required=False,
        label="Or create a new skill",
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Example: Public Speaking'
        })
    )
    level = forms.ChoiceField(
        choices=UserSkill.LEVEL_CHOICES,
        required=True,
        label="Skill Level",
        widget=forms.Select(attrs={
            'class': 'w-full border border-gray-300 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        existing = cleaned_data.get("existing_skill")
        new = cleaned_data.get("new_skill")

        if new:
            new = new.strip()
            cleaned_data["new_skill"] = new

        if not existing and not new:
            raise forms.ValidationError("Please select a skill or enter a new one.")

        if existing and new:
            raise forms.ValidationError("Choose either an existing skill OR enter a new one, not both.")

        return cleaned_data


from django import forms
import json

INPUT_CLASS = (
    "w-full block rounded-xl border-2 border-gray-300 bg-white "
    "px-4 py-3 text-gray-900 placeholder-gray-400 shadow-sm "
    "focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
)

TEXTAREA_CLASS = (
    "w-full block rounded-xl border-2 border-gray-300 bg-white "
    "px-4 py-3 text-gray-900 placeholder-gray-400 shadow-sm "
    "focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 min-h-[120px]"
)

SELECT_CLASS = (
    "w-full block rounded-xl border-2 border-gray-300 bg-white "
    "px-4 py-3 text-gray-900 shadow-sm "
    "focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
)

CHECKBOX_CLASS = "mt-1 h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"


class UserProfileForm(forms.ModelForm):
    availability_json = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )

    cultural_interest_other = forms.CharField(
        required=False,
        label="Other cultural interests",
        widget=forms.TextInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "Example: Tea ceremony, folk dance, local cuisine, sign language"
        })
    )

    class Meta:
        model = UserProfile
        fields = [
            "prefers_online",
            "prefers_inperson",
            "safety_notes",
            "city",
            "country",
            "enable_smart_matching",
            "interested_in_cultural_exchange",
            "cultural_skills_wanted",
            "cultural_interest_other",
        ]

        labels = {
            "prefers_online": "Prefer online",
            "prefers_inperson": "Prefer in-person",
            "interested_in_cultural_exchange": "I’m interested in cultural exchange",
            "cultural_skills_wanted": "What cultural topics or skills interest you?",
        }
        widgets = {
            "city": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Enter your city"
            }),
            "country": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Enter your country"
            }),
            "safety_notes": forms.Textarea(attrs={
                "class": TEXTAREA_CLASS,
                "placeholder": "Optional: share any comfort, boundary, or meeting preferences"
            }),
            "cultural_skills_wanted": forms.SelectMultiple(attrs={
                "class": SELECT_CLASS,
                "size": 6
            }),
            "prefers_online": forms.CheckboxInput(attrs={
                "class": CHECKBOX_CLASS
            }),
            "prefers_inperson": forms.CheckboxInput(attrs={
                "class": CHECKBOX_CLASS
            }),
            "enable_smart_matching": forms.CheckboxInput(attrs={
                "class": CHECKBOX_CLASS
            }),
            "interested_in_cultural_exchange": forms.CheckboxInput(attrs={
                "class": CHECKBOX_CLASS
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk and self.instance.availability:
            self.fields["availability_json"].initial = json.dumps(self.instance.availability)
        else:
            self.fields["availability_json"].initial = "[]"

    def clean_availability_json(self):
        raw = self.cleaned_data.get("availability_json", "").strip()

        if not raw:
            return []

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            raise forms.ValidationError("Invalid availability data.")

        if not isinstance(data, list):
            raise forms.ValidationError("Availability must be a list of time slots.")

        for slot in data:
            if not isinstance(slot, dict):
                raise forms.ValidationError("Each availability slot must be an object.")

            if not all(key in slot for key in ["day", "start", "end"]):
                raise forms.ValidationError("Each availability slot must include day, start, and end.")

        return data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.availability = self.cleaned_data.get("availability_json", [])

        if commit:
            instance.save()
            self.save_m2m()

        return instance
    
INPUT_CLASS = (
    "w-full block rounded-xl border-2 border-gray-300 bg-white "
    "px-4 py-3 text-gray-900 placeholder-gray-400 "
    "shadow-sm outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 "
    "transition"
)

class AccountUpdateForm(forms.ModelForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "Enter your email",
            "autocomplete": "email",
        })
    )

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "Choose a username",
            "autocomplete": "username",
        })
    )

    class Meta:
        model = User
        fields = ["username", "email"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_username(self):
        username = self.cleaned_data["username"]
        qs = User.objects.filter(username__iexact=username)
        if self.user:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise forms.ValidationError("That username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        qs = User.objects.filter(email__iexact=email)
        if self.user:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise forms.ValidationError("That email is already in use.")
        return email
from django import forms

INPUT_CLASS = (
    "w-full block rounded-xl border-2 border-gray-300 bg-white "
    "px-4 py-3 text-gray-900 placeholder-gray-400 shadow-sm "
    "focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
)

TEXTAREA_CLASS = (
    "w-full block rounded-xl border-2 border-gray-300 bg-white "
    "px-4 py-3 text-gray-900 placeholder-gray-400 shadow-sm "
    "focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 min-h-[100px]"
)

SELECT_CLASS = (
    "w-full block rounded-xl border-2 border-gray-300 bg-white "
    "px-4 py-3 text-gray-900 shadow-sm "
    "focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
)

CHECKBOX_CLASS = "mt-1 h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"


class OfferForm(forms.ModelForm):
    requested_skill_name = forms.CharField(
        label="What would you like to learn?",
        widget=forms.TextInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "Example: Guitar, Spanish, Cooking, Public speaking"
        })
    )

    class Meta:
        model = Offer
        fields = [
            "description",
            "offered_skill",
            "requested_skill_name",
            "prefers_online",
            "prefers_inperson",
            "multiple_sessions",
            "suggested_location",
        ]

        labels = {
            "description": "Describe your offer",
            "offered_skill": "What skill are you offering?",
            "prefers_online": "I’m open to online sessions",
            "prefers_inperson": "I’m open to in-person sessions",
            "multiple_sessions": "This may require multiple sessions",
            "suggested_location": "Suggested meeting location",
        }

        help_texts = {
            "description": "Explain what you can teach and what you’re looking for in return.",
            "suggested_location": "Optional — suggest a public place if meeting in person.",
        }

        widgets = {
            "description": forms.Textarea(attrs={
                "class": TEXTAREA_CLASS,
                "placeholder": "Example: I can help you practice conversational Spanish. In return, I'd love help learning guitar."
            }),
            "offered_skill": forms.Select(attrs={
                "class": SELECT_CLASS
            }),
            "suggested_location": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Example: Coffee shop, library, online"
            }),
            "prefers_online": forms.CheckboxInput(attrs={
                "class": CHECKBOX_CLASS
            }),
            "prefers_inperson": forms.CheckboxInput(attrs={
                "class": CHECKBOX_CLASS
            }),
            "multiple_sessions": forms.CheckboxInput(attrs={
                "class": CHECKBOX_CLASS
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

        self.fields["offered_skill"].queryset = Skill.objects.filter(
            id__in=UserSkill.objects.filter(user=user).values_list("skill_id", flat=True)
        )

# -------------------------
# RESCHEDULE SESSION FORM
# -------------------------
class RescheduleSessionForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            "type": "date",
            "class": "w-full rounded-xl border-2 border-gray-300 px-4 py-3"
        })
    )

    time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            "type": "time",
            "class": "w-full rounded-xl border-2 border-gray-300 px-4 py-3"
        })
    )

    session_type = forms.ChoiceField(
        required=False,
        choices=[
            ("", "Auto choose based on shared preferences"),
            ("online", "Online"),
            ("inperson", "In Person"),
        ],
        widget=forms.Select(attrs={
            "class": "w-full rounded-xl border-2 border-gray-300 px-4 py-3"
        })
    )

    class Meta:
        model = Session
        fields = []  # ❗ we handle fields manually

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        super().__init__(*args, **kwargs)

        if instance and instance.date:
            local_dt = timezone.localtime(instance.date)

            self.fields["date"].initial = local_dt.date()
            self.fields["time"].initial = local_dt.time().replace(second=0, microsecond=0)

        if instance and instance.type:
            self.fields["session_type"].initial = instance.type

    def clean(self):
        cleaned_data = super().clean()

        date = cleaned_data.get("date")
        time = cleaned_data.get("time")

        if not date or not time:
            raise forms.ValidationError("Please provide both date and time.")

        naive_dt = datetime.combine(date, time)
        aware_dt = timezone.make_aware(
            naive_dt,
            timezone.get_current_timezone()
        )

        if aware_dt <= timezone.now():
            raise forms.ValidationError("New session time must be in the future.")

        cleaned_data["combined_datetime"] = aware_dt
        return cleaned_data

    def save(self, commit=True):
        instance = self.instance

        combined_dt = self.cleaned_data["combined_datetime"]
        session_type = self.cleaned_data.get("session_type")

        instance.date = combined_dt

        if session_type:
            instance.type = session_type

        if commit:
            instance.save()

        return instance

from django.contrib.auth.forms import PasswordResetForm

class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "Enter your email address",
            "autocomplete": "email",
        })
    )

from django.contrib.auth.forms import SetPasswordForm

class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "Enter your new password",
            "autocomplete": "new-password",
        })
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "Confirm your new password",
            "autocomplete": "new-password",
        })
    )