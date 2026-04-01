from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Avg

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    prefers_online = models.BooleanField(default=True)
    prefers_inperson = models.BooleanField(default=False)
    
    # Structured availability
    # Example: [{"day":"Mon","start":"14:00","end":"16:00"}]
    availability = models.JSONField(blank=True, null=True)
    
    safety_notes = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    interested_in_cultural_exchange = models.BooleanField(default=False)
    cultural_skills_wanted = models.ManyToManyField('Skill', blank=True, related_name='cultural_wanting_users')
    
    enable_smart_matching = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s profile"

# ---------------------
# SKILLS
# ---------------------
class Skill(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)  # e.g., 'Music', 'Programming', 'Language'
    tags = models.CharField(max_length=200, blank=True)  # comma-separated tags
    description = models.TextField(blank=True)  # optional skill description

    def __str__(self):
        return self.name


class UserSkill(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    
    # Optional: level for matching & recommendation purposes
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner')
    
    class Meta:
        unique_together = ('user', 'skill')

    def __str__(self):
        return f"{self.user.username} - {self.skill.name} ({self.level})"


# ---------------------
# OFFERS
# ---------------------
class Offer(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('matched', 'Matched'),
        ('closed', 'Closed'),
    ]

    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')

    offered_skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='offers_as_offered'
    )
    requested_skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='offers_as_requested'
    )

    matched_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='matched_offers'
    )

    # Support multiple session exchanges
    multiple_sessions = models.BooleanField(default=False)

    # Optional suggested location for in-person
    suggested_location = models.CharField(max_length=200, blank=True)

    # Preferred session types
    prefers_online = models.BooleanField(default=True)
    prefers_inperson = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.creator.username} offers {self.offered_skill.name}"


# ---------------------
# SESSION
# ---------------------
class Session(models.Model):
    TYPE_CHOICES = [
        ('online', 'Online'),
        ('inperson', 'In Person'),
    ]

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    offer = models.ForeignKey(Offer, on_delete=models.CASCADE)
    date = models.DateTimeField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')

    # Optional suggested location or platform (filled by smart suggestions)
    suggested_location_or_platform = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session {self.id} on {self.date} ({self.type})"


# ---------------------
# SESSION PARTICIPANTS
# ---------------------
class SessionParticipant(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('session', 'user')

    def __str__(self):
        return f"{self.user.username} in session {self.session.id}"


# ---------------------
# RATINGS (Improved)
# ---------------------
class Rating(models.Model):
    score = models.IntegerField()
    comment = models.TextField(blank=True)
    date = models.DateTimeField(auto_now_add=True)

    giver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='given_ratings'
    )
    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_ratings'
    )

    class Meta:
        unique_together = ('giver', 'receiver')  # One rating per user pair (can adjust if you want multiple)

    def clean(self):
        # Prevent self-rating
        if self.giver == self.receiver:
            raise ValidationError("You cannot rate yourself.")

        # Ensure giver and receiver have at least one completed session together
        common_sessions = SessionParticipant.objects.filter(
            session__in=Session.objects.filter(status='completed'),
            user=self.giver
        ).filter(
            session__in=SessionParticipant.objects.filter(user=self.receiver).values_list('session_id', flat=True)
        ).exists()

        if not common_sessions:
            raise ValidationError("You can only rate a user after at least one completed session together.")

    def __str__(self):
        return f"Rating {self.score} for {self.receiver.username} by {self.giver.username}"
    

def average_rating(self):
    # Aggregate all ratings received by this user
    result = self.received_ratings.aggregate(avg=Avg('score'))['avg']
    return round(result, 2) if result is not None else None

# Attach the method to User
User.add_to_class("average_rating", average_rating)


class MatchRequest(models.Model):
    offer = models.ForeignKey('Offer', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_requests')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_requests')

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    used_smart_matching = models.BooleanField(default=False)

    def clean(self):
        if self.sender == self.receiver:
            raise ValidationError("Cannot send a match request to yourself.")
        
        sender_avail = self.sender.userprofile.availability
        receiver_avail = self.receiver.userprofile.availability
        if sender_avail and receiver_avail and not self._availability_overlap(sender_avail, receiver_avail):
            raise ValidationError("No overlapping availability for this match request.")

    def _availability_overlap(self, avail1, avail2):
        """Check if two availability JSON lists overlap (partial overlap counts)."""
        for slot1 in avail1:
            start1 = datetime.strptime(slot1["start"], "%H:%M").time()
            end1 = datetime.strptime(slot1["end"], "%H:%M").time()
            day1 = slot1["day"]

            for slot2 in avail2:
                start2 = datetime.strptime(slot2["start"], "%H:%M").time()
                end2 = datetime.strptime(slot2["end"], "%H:%M").time()
                day2 = slot2["day"]

                if day1 != day2:
                    continue  # different day

                latest_start = max(start1, start2)
                earliest_end = min(end1, end2)
                if latest_start < earliest_end:
                    return True  # overlap exists
        return False

    def __str__(self):
        return f"Request from {self.sender} to {self.receiver} for offer {self.offer.id}"

    
class Message(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, null=True, blank=True)
    match_request = models.ForeignKey(MatchRequest, on_delete=models.CASCADE, null=True, blank=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')

    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        target = self.match_request.id if self.match_request else self.offer.id
        return f"Message from {self.sender} to {self.receiver} (target {target})"

# ---------------------
# SMART MATCH RECOMMENDATIONS
# ---------------------
def get_recommended_matches(user, use_smart=True):
    user_skills = UserSkill.objects.filter(user=user).values_list('skill_id', flat=True)
    offers = Offer.objects.filter(requested_skill_id__in=user_skills, status='open').exclude(creator=user)

    recommendations = []
    for offer in offers:
        score = 0

        # Skill match weight
        score += 50

        # Ratings
        avg_rating = offer.creator.received_ratings.aggregate(Avg('score'))['score__avg'] or 0
        score += avg_rating * 5

        # Preference match
        profile = offer.creator.userprofile
        if user.userprofile.prefers_online and profile.prefers_online:
            score += 10
        if user.userprofile.prefers_inperson and profile.prefers_inperson:
            score += 10

        # Location proximity
        if user.userprofile.city and profile.city and user.userprofile.city == profile.city:
            score += 15

        # Optional: skip if smart matching enabled and no availability overlap
        if use_smart and user.userprofile.enable_smart_matching and offer.creator.userprofile.enable_smart_matching:
            if user.userprofile.availability and profile.availability:
                mr = MatchRequest(sender=user, receiver=offer.creator, offer=offer)
                if not mr._availability_overlap(user.userprofile.availability, profile.availability):
                    continue

        recommendations.append((offer, score))

    recommendations.sort(key=lambda x: x[1], reverse=True)
    return recommendations

def get_cultural_recommendations(user):
    """
    Returns users and their offered skills that match the current user's cultural interests.
    This is separate from the normal Offer-based matching flow.
    """
    profile = user.userprofile

    # If user hasn't opted into cultural discovery, return empty
    if not profile.interested_in_cultural_exchange:
        return []

    # IDs of skills the user wants to explore culturally
    wanted_skill_ids = profile.cultural_skills_wanted.values_list('id', flat=True)

    # Find other users who are also interested in cultural exchange
    # and have at least one skill the current user wants
    other_users = User.objects.filter(
        userprofile__interested_in_cultural_exchange=True
    ).exclude(id=user.id).distinct()

    results = []

    for u in other_users:
        # Find the skills of this user that match the current user's cultural interests
        matching_skills = u.userskill_set.filter(skill_id__in=wanted_skill_ids)

        if matching_skills.exists():
            results.append({
                "user": u,
                "matching_skills": matching_skills
            })

    # Optional: sort by average rating, shared location, or other preference
    results.sort(key=lambda x: x['user'].average_rating() or 0, reverse=True)

    return results


def get_user_categories(user):
    # Categories of skills the user can teach
    offered_categories = Skill.objects.filter(
        id__in=UserSkill.objects.filter(user=user).values_list('skill_id', flat=True)
    ).values_list('category', flat=True)

    # Categories of skills the user has requested in past offers
    requested_categories = Offer.objects.filter(
        creator=user
    ).values_list('requested_skill__category', flat=True)

    # Combine and deduplicate
    categories = set(offered_categories) | set(requested_categories)

    return list(categories)
def get_category_recommendations(user):
    categories = get_user_categories(user)

    if not categories:
        return []

    offers = Offer.objects.filter(
        offered_skill__category__in=categories,
        status='open'
    ).exclude(creator=user)

    return offers

from datetime import timedelta, datetime
from django.utils import timezone

def create_sessions_from_match(match_request, session_dates_times, session_type=None, use_smart_location=True):
    sessions = []

    sender_profile = match_request.sender.userprofile
    receiver_profile = match_request.receiver.userprofile

    if not session_type:
        if sender_profile.prefers_online and receiver_profile.prefers_online:
            session_type = 'online'
        elif sender_profile.prefers_inperson and receiver_profile.prefers_inperson:
            session_type = 'inperson'
        else:
            session_type = 'online'

    suggested_location = ""
    if use_smart_location:
        if session_type == 'inperson' and receiver_profile.city:
            suggested_location = f"Meet at a safe public space in {receiver_profile.city}"
        elif session_type == 'online':
            suggested_location = "Suggested online platform: Zoom / Discord / WhatsApp"

    for dt in session_dates_times:
        dt_obj = datetime.strptime(f"{dt['date']} {dt['time']}", "%Y-%m-%d %H:%M")
        if dt_obj < timezone.now():
            continue

        session = Session.objects.create(
            offer=match_request.offer,
            date=dt_obj,
            type=session_type,
            suggested_location_or_platform=suggested_location
        )

        SessionParticipant.objects.create(session=session, user=match_request.sender)
        SessionParticipant.objects.create(session=session, user=match_request.receiver)
        sessions.append(session)

    return sessions