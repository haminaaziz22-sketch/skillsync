from django import forms
from .models import Session, Skill, UserSkill, Offer

class UserSkillForm(forms.Form):
    existing_skill = forms.ModelChoiceField(
        queryset=Skill.objects.all(),
        required=False,
        label="Choose a skill"
    )
    new_skill = forms.CharField(
        max_length=100,
        required=False,
        label="Or create a new skill"
    )

    def clean(self):
        cleaned_data = super().clean()
        existing = cleaned_data.get("existing_skill")
        new = cleaned_data.get("new_skill")

        # Normalize input (prevents spaces like "   ")
        if new:
            new = new.strip()
            cleaned_data["new_skill"] = new

        # ❌ Nothing entered
        if not existing and not new:
            raise forms.ValidationError("Please select a skill or enter a new one.")

        # ❌ BOTH entered (important fix)
        if existing and new:
            raise forms.ValidationError("Choose either an existing skill OR enter a new one, not both.")

        return cleaned_data



class OfferForm(forms.ModelForm):
    requested_skill_name = forms.CharField(label="Requested Skill")

    class Meta:
        model = Offer
        fields = ['description', 'offered_skill', 'requested_skill_name']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')  # get the logged-in user
        super().__init__(*args, **kwargs)

        # Only show skills the user actually has
        self.fields['offered_skill'].queryset = Skill.objects.filter(
            id__in=UserSkill.objects.filter(user=user).values_list('skill_id', flat=True)
        )

class RescheduleSessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ['date', 'type']


from .models import UserProfile

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'prefers_online',
            'prefers_inperson',
            'availability',
            'safety_notes',
            'city',
            'country',
        ]
