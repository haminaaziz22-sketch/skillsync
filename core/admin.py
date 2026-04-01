from django.contrib import admin
from .models import Skill, UserSkill, Offer, Session, SessionParticipant, Rating

admin.site.register(Skill)
admin.site.register(UserSkill)
admin.site.register(Offer)
admin.site.register(Session)
admin.site.register(SessionParticipant)
admin.site.register(Rating)