from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Avg
from datetime import datetime
from django.db import transaction
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='userprofile'
    )

    prefers_online = models.BooleanField(default=True)
    prefers_inperson = models.BooleanField(default=False)

    # Example:
    # [
    #   {"day": "Mon", "start": "14:00", "end": "16:00"}
    # ]
    availability = models.JSONField(blank=True, null=True)

    safety_notes = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)

    interested_in_cultural_exchange = models.BooleanField(default=False)
    cultural_skills_wanted = models.ManyToManyField(
        'Skill',
        blank=True,
        related_name='cultural_wanting_users'
    )
    cultural_interest_other = models.CharField(max_length=255, blank=True)

    enable_smart_matching = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s profile"


# ---------------------
# SKILLS
# ---------------------
class Skill(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)  # e.g. Music, Programming, Language
    tags = models.CharField(max_length=200, blank=True)  # comma-separated tags
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class UserSkill(models.Model):
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_skills'
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='user_skills'
    )
    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default='beginner'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'skill'],
                name='unique_user_skill'
            )
        ]

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

    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_offers'
    )
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')

    offered_skill = models.ForeignKey(
        'Skill',
        on_delete=models.CASCADE,
        related_name='offers_as_offered'
    )
    requested_skill = models.ForeignKey(
        'Skill',
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

    multiple_sessions = models.BooleanField(default=False)
    suggested_location = models.CharField(max_length=200, blank=True)

    prefers_online = models.BooleanField(default=True)
    prefers_inperson = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        errors = {}

        if self.offered_skill_id and self.requested_skill_id:
            if self.offered_skill_id == self.requested_skill_id:
                errors['requested_skill'] = "Offered skill and requested skill cannot be the same."

        if self.matched_user_id:
            if self.matched_user_id == self.creator_id:
                errors['matched_user'] = "Matched user cannot be the offer creator."

            if self.status != 'matched':
                errors['status'] = "Status must be 'matched' when a matched user is set."

        if self.status == 'matched' and not self.matched_user_id:
            errors['matched_user'] = "A matched offer must have a matched user."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

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

    offer = models.ForeignKey(
        Offer,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sessions'
    )

    cultural_request = models.ForeignKey(
        'CulturalConnectionRequest',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sessions'
    )

    date = models.DateTimeField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')

    suggested_location_or_platform = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        errors = {}

        targets = [self.offer, self.cultural_request]
        filled_targets = [target for target in targets if target is not None]

        if len(filled_targets) == 0:
            errors['offer'] = "A session must belong to an offer or a cultural connection."

        if len(filled_targets) > 1:
            errors['offer'] = "A session can belong to only one target at a time."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.offer:
            target = f"offer #{self.offer.id}"
        elif self.cultural_request:
            target = f"cultural request #{self.cultural_request.id}"
        else:
            target = "no target"

        return f"Session {self.id} on {self.date} ({self.type}) for {target}"


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
# RATINGS
# ---------------------
from django.core.validators import MinValueValidator, MaxValueValidator

class Rating(models.Model):
    score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
        constraints = [
            models.UniqueConstraint(
                fields=['giver', 'receiver'],
                name='unique_rating_per_user_pair'
            )
        ]

    def clean(self):
        errors = {}

        if not self.giver_id:
            errors['giver'] = "A rating must have a giver."

        if not self.receiver_id:
            errors['receiver'] = "A rating must have a receiver."

        if self.giver_id and self.receiver_id:
            if self.giver_id == self.receiver_id:
                errors['receiver'] = "You cannot rate yourself."

            common_sessions = SessionParticipant.objects.filter(
                user=self.giver,
                session__status='completed'
            ).filter(
                session__sessionparticipant__user=self.receiver
            ).exists()

            if not common_sessions:
                errors['__all__'] = (
                    "You can only rate a user after at least one completed session together."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Rating {self.score} for {self.receiver.username} by {self.giver.username}"


def average_rating(self):
    result = self.received_ratings.aggregate(avg=Avg('score'))['avg']
    return round(result, 2) if result is not None else None


User.add_to_class("average_rating", average_rating)


class MatchRequest(models.Model):
    offer = models.ForeignKey(
        Offer,
        on_delete=models.CASCADE,
        related_name='match_requests'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_requests'
    )
    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_requests'
    )

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    used_smart_matching = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['offer', 'sender', 'receiver'],
                name='unique_match_request_per_offer_sender_receiver'
            )
        ]

    def clean(self):
        errors = {}

        if self.sender_id == self.receiver_id:
            errors['receiver'] = "Cannot send a match request to yourself."

        if not self.offer_id:
            errors['offer'] = "A match request must belong to an offer."

        if self.offer_id and self.sender_id and self.receiver_id:
            if self.receiver_id != self.offer.creator_id:
                errors['receiver'] = "Receiver must be the creator of the offer."

            if self.sender_id == self.offer.creator_id:
                errors['sender'] = "You cannot send a match request to your own offer."

            if self.offer.status != 'open':
                errors['offer'] = "You can only send a match request for an open offer."

            has_required_skill = UserSkill.objects.filter(
                user=self.sender,
                skill=self.offer.requested_skill
            ).exists()
            if not has_required_skill:
                errors['sender'] = (
                    f"Sender must have the requested skill: {self.offer.requested_skill.name}."
                )

        if errors:
            raise ValidationError(errors)

    def _availability_overlap(self, avail1, avail2):
        for slot1 in avail1:
            try:
                day1 = slot1["day"]
                start1 = datetime.strptime(slot1["start"], "%H:%M").time()
                end1 = datetime.strptime(slot1["end"], "%H:%M").time()
            except (KeyError, ValueError, TypeError):
                continue

            for slot2 in avail2:
                try:
                    day2 = slot2["day"]
                    start2 = datetime.strptime(slot2["start"], "%H:%M").time()
                    end2 = datetime.strptime(slot2["end"], "%H:%M").time()
                except (KeyError, ValueError, TypeError):
                    continue

                if day1 != day2:
                    continue

                latest_start = max(start1, start2)
                earliest_end = min(end1, end2)

                if latest_start < earliest_end:
                    return True

        return False

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Request from {self.sender.username} to {self.receiver.username} for offer {self.offer.id}"

from django.db.models import Avg


def get_recommended_matches(user, use_smart=True):
    user_profile = getattr(user, 'userprofile', None)
    if not user_profile:
        return []

    user_skill_ids = UserSkill.objects.filter(
        user=user
    ).values_list('skill_id', flat=True)

    offers = Offer.objects.filter(
        requested_skill_id__in=user_skill_ids,
        status='open'
    ).exclude(
        creator=user
    ).select_related(
        'creator',
        'creator__userprofile',
        'requested_skill',
        'offered_skill'
    )

    recommendations = []

    for offer in offers:
        creator = offer.creator
        creator_profile = getattr(creator, 'userprofile', None)
        if not creator_profile:
            continue

        score = 50
        reasons = ["Matches your requested skill"]

        avg_rating = creator.received_ratings.aggregate(avg=Avg('score'))['avg'] or 0
        if avg_rating:
            score += avg_rating * 5
            if avg_rating >= 4:
                reasons.append(f"Highly rated ({round(avg_rating, 1)})")

        if user_profile.city and creator_profile.city and user_profile.city == creator_profile.city:
            score += 15
            reasons.append("Same city")

        if user_profile.prefers_online and creator_profile.prefers_online:
            score += 10
            reasons.append("Both prefer online")
        elif user_profile.prefers_inperson and creator_profile.prefers_inperson:
            score += 10
            reasons.append("Both prefer in-person")

        availability_overlap = False

        if user_profile.availability and creator_profile.availability:
            temp_request = MatchRequest(
                offer=offer,
                sender=user,
                receiver=creator,
                used_smart_matching=True
            )

            availability_overlap = temp_request._availability_overlap(
                user_profile.availability,
                creator_profile.availability
            )

            if availability_overlap:
                score += 15
                reasons.append("Overlapping availability")

            # Strict smart-matching filter only if BOTH sides enabled it
            if (
                use_smart
                and user_profile.enable_smart_matching
                and creator_profile.enable_smart_matching
                and not availability_overlap
            ):
                continue

        recommendations.append({
            'offer': offer,
            'score': round(score, 1),
            'reasons': reasons,
            'creator': creator,
            'rating': round(avg_rating, 1) if avg_rating else None,
            'availability_overlap': availability_overlap,
        })

    recommendations.sort(key=lambda item: item['score'], reverse=True)
    return recommendations
    
class Message(models.Model):
    offer = models.ForeignKey(
        Offer,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='messages'
    )
    match_request = models.ForeignKey(
        MatchRequest,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='messages'
    )
    cultural_request = models.ForeignKey(
        'CulturalConnectionRequest',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='messages'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_messages'
    )

    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def clean(self):
        errors = {}

        targets = [self.offer, self.match_request, self.cultural_request]
        filled_targets = [target for target in targets if target is not None]

        if len(filled_targets) > 1:
            errors["offer"] = "A message can belong to only one conversation target."
        elif len(filled_targets) == 0:
            errors["offer"] = "A message must belong to an offer, match request, or cultural request."

        if self.sender == self.receiver:
            errors["receiver"] = "Sender and receiver cannot be the same user."

        if self.offer:
            allowed_users = {self.offer.creator_id}
            if self.offer.matched_user_id:
                allowed_users.add(self.offer.matched_user_id)

            if self.sender_id not in allowed_users:
                errors["sender"] = "Sender is not part of this offer conversation."
            if self.receiver_id not in allowed_users:
                errors["receiver"] = "Receiver is not part of this offer conversation."

        if self.match_request:
            allowed_users = {
                self.match_request.sender_id,
                self.match_request.receiver_id,
            }

            if self.sender_id not in allowed_users:
                errors["sender"] = "Sender is not part of this match request conversation."
            if self.receiver_id not in allowed_users:
                errors["receiver"] = "Receiver is not part of this match request conversation."

        if self.cultural_request:
            allowed_users = {
                self.cultural_request.sender_id,
                self.cultural_request.receiver_id,
            }

            if self.sender_id not in allowed_users:
                errors["sender"] = "Sender is not part of this cultural conversation."
            if self.receiver_id not in allowed_users:
                errors["receiver"] = "Receiver is not part of this cultural conversation."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class CulturalConnectionRequest(models.Model):
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_cultural_requests'
    )
    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_cultural_requests'
    )

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    initial_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['sender', 'receiver'],
                name='unique_cultural_request_sender_receiver'
            )
        ]

    def clean(self):
        errors = {}

        if self.sender_id == self.receiver_id:
            errors['receiver'] = "You cannot send a cultural request to yourself."

        sender_profile = getattr(self.sender, 'userprofile', None) if self.sender_id else None
        receiver_profile = getattr(self.receiver, 'userprofile', None) if self.receiver_id else None

        if sender_profile and not sender_profile.interested_in_cultural_exchange:
            errors['sender'] = "You must enable cultural discovery first."

        if receiver_profile and not receiver_profile.interested_in_cultural_exchange:
            errors['receiver'] = "This user is not accepting cultural discovery requests."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Cultural request from {self.sender.username} to {self.receiver.username}"



import re


def _normalize_text(value):
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def _split_terms(value):
    """
    Split comma-separated or free text into normalized terms.
    Example:
    "Tea ceremony, folk dance, local cuisine"
    -> {"tea ceremony", "folk dance", "local cuisine"}
    """
    if not value:
        return set()

    parts = re.split(r"[,\n;/]+", str(value))
    cleaned = {_normalize_text(part) for part in parts if _normalize_text(part)}
    return cleaned


def _skill_tag_set(skill):
    """
    Convert a skill's comma-separated tags into a normalized set.
    """
    if not skill or not skill.tags:
        return set()
    return _split_terms(skill.tags)


def get_cultural_recommendations(user):
    profile = getattr(user, "userprofile", None)
    if not profile or not profile.interested_in_cultural_exchange:
        return []

    wanted_skills = list(profile.cultural_skills_wanted.all())
    wanted_skill_ids = {skill.id for skill in wanted_skills}

    my_skill_qs = UserSkill.objects.filter(user=user).select_related("skill")
    my_skills = list(my_skill_qs)
    my_skill_ids = {user_skill.skill_id for user_skill in my_skills}

    my_custom_terms = _split_terms(profile.cultural_interest_other)

    # Build discovery anchors from selected interests + user's own cultural-ish skills
    anchor_skills = list(wanted_skills)

    # If the user enabled cultural discovery but did not pick explicit interests,
    # fall back to their own skills as discovery anchors.
    if not anchor_skills:
        anchor_skills = [user_skill.skill for user_skill in my_skills]

    # Still nothing to work from
    if not anchor_skills and not my_custom_terms:
        return []

    anchor_skill_ids = {skill.id for skill in anchor_skills}

    anchor_categories = {
        _normalize_text(skill.category)
        for skill in anchor_skills
        if skill.category
    }

    anchor_tags = set()
    anchor_names = set()
    for skill in anchor_skills:
        anchor_tags.update(_skill_tag_set(skill))
        anchor_names.add(_normalize_text(skill.name))

    other_users = (
        User.objects.filter(userprofile__interested_in_cultural_exchange=True)
        .exclude(id=user.id)
        .select_related("userprofile")
        .distinct()
    )

    results = []

    for other_user in other_users:
        other_profile = getattr(other_user, "userprofile", None)
        if not other_profile:
            continue

        other_user_skills = list(
            UserSkill.objects.filter(user=other_user).select_related("skill")
        )
        if not other_user_skills:
            continue

        # 1) Exact matches to explicitly selected wanted skills
        exact_matching_skills = [
            user_skill for user_skill in other_user_skills
            if user_skill.skill_id in wanted_skill_ids
        ]

        # 2) Related matches based on anchor categories
        category_matching_skills = [
            user_skill for user_skill in other_user_skills
            if _normalize_text(user_skill.skill.category) in anchor_categories
            and user_skill.skill_id not in wanted_skill_ids
        ]

        # 3) Related matches based on anchor tags
        tag_matching_skills = []
        for user_skill in other_user_skills:
            skill_tags = _skill_tag_set(user_skill.skill)
            if skill_tags.intersection(anchor_tags) and user_skill.skill_id not in wanted_skill_ids:
                tag_matching_skills.append(user_skill)

        # 4) Related matches based on custom typed interests
        custom_interest_matches = []
        if my_custom_terms:
            for user_skill in other_user_skills:
                skill_name = _normalize_text(user_skill.skill.name)
                skill_category = _normalize_text(user_skill.skill.category)
                skill_tags = _skill_tag_set(user_skill.skill)

                searchable_terms = {skill_name, skill_category, *skill_tags}

                # exact term match
                if any(term in searchable_terms for term in my_custom_terms):
                    custom_interest_matches.append(user_skill)
                    continue

                # softer contains-based match for free text like "tea" vs "tea ceremony"
                if any(
                    term in skill_name or term in skill_category or any(term in tag for tag in skill_tags)
                    for term in my_custom_terms
                ):
                    custom_interest_matches.append(user_skill)

        # 5) If user has no explicit selected interests, allow discovery-only matches
        has_any_match = (
            exact_matching_skills
            or category_matching_skills
            or tag_matching_skills
            or custom_interest_matches
        )

        if not has_any_match:
            continue

        # Skills THEY want that I have
        their_wanted_skill_ids = set(
            other_profile.cultural_skills_wanted.values_list("id", flat=True)
        )
        reciprocal_skill_ids = my_skill_ids.intersection(their_wanted_skill_ids)

        reciprocal_skills = [
            user_skill for user_skill in my_skills
            if user_skill.skill_id in reciprocal_skill_ids
        ]

        avg_rating = other_user.average_rating() or 0
        same_city = bool(
            profile.city and
            other_profile.city and
            _normalize_text(profile.city) == _normalize_text(other_profile.city)
        )

        score = 0
        reasons = []

        # Strongest weight: exact explicit matches
        if exact_matching_skills:
            score += 45 + (len(exact_matching_skills) * 8)
            reasons.append("Has cultural skills you explicitly want to explore")

        # Discovery weights
        if category_matching_skills:
            score += 18 + (len(category_matching_skills) * 4)
            reasons.append("Has skills in related cultural categories")

        if tag_matching_skills:
            score += 14 + (len(tag_matching_skills) * 3)
            reasons.append("Has skills with related cultural tags")

        if custom_interest_matches:
            score += 16 + (len(custom_interest_matches) * 3)
            reasons.append("Matches your custom cultural interests")

        if reciprocal_skills:
            score += 20 + (len(reciprocal_skills) * 4)
            reasons.append("May also be interested in skills you have")

        if same_city:
            score += 10
            reasons.append("Same city")

        if avg_rating >= 4.5:
            score += 12
            reasons.append(f"Excellent rating ({round(avg_rating, 1)})")
        elif avg_rating >= 4.0:
            score += 8
            reasons.append(f"Highly rated ({round(avg_rating, 1)})")
        elif avg_rating >= 3.0:
            score += 4
            reasons.append(f"Well rated ({round(avg_rating, 1)})")

        def dedupe_user_skills(user_skill_list):
            seen = set()
            deduped = []
            for item in user_skill_list:
                if item.skill_id not in seen:
                    seen.add(item.skill_id)
                    deduped.append(item)
            return deduped

        exact_matching_skills = dedupe_user_skills(exact_matching_skills)
        category_matching_skills = dedupe_user_skills(category_matching_skills)
        tag_matching_skills = dedupe_user_skills(tag_matching_skills)
        custom_interest_matches = dedupe_user_skills(custom_interest_matches)
        reciprocal_skills = dedupe_user_skills(reciprocal_skills)

        # Use exact matches as the main "matching_skills" bucket so your template stays compatible
        matching_skills = exact_matching_skills

        # Mark whether this result is primarily direct or discovery-based
        match_type = "direct" if exact_matching_skills else "discovery"

        results.append({
            "user": other_user,
            "score": score,
            "match_type": match_type,
            "matching_skills": matching_skills,
            "category_matching_skills": category_matching_skills,
            "tag_matching_skills": tag_matching_skills,
            "custom_interest_matches": custom_interest_matches,
            "reciprocal_skills": reciprocal_skills,
            "average_rating": round(avg_rating, 1) if avg_rating else None,
            "same_city": same_city,
            "reasons": reasons,
        })

    results.sort(
        key=lambda item: (
            item["score"],
            item["match_type"] == "direct",
            item["average_rating"] or 0,
            len(item["reciprocal_skills"]),
            item["same_city"],
        ),
        reverse=True
    )

    return results



from datetime import datetime
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone


def create_sessions_from_target(
    target,
    session_dates_times,
    session_type=None,
    use_smart_location=True,
):
    """
    Create one or more Session objects from either:
    - MatchRequest
    - CulturalConnectionRequest

    session_dates_times format:
    [
        {"date": "2026-04-20", "time": "14:30"},
        {"date": "2026-04-21", "time": "10:00"},
    ]
    """

    if not isinstance(target, (MatchRequest, CulturalConnectionRequest)):
        raise ValidationError("Invalid target type for session creation.")

    if target.status != "accepted":
        raise ValidationError("Sessions can only be created from an accepted request.")

    sender = target.sender
    receiver = target.receiver

    sender_profile = getattr(sender, "userprofile", None)
    receiver_profile = getattr(receiver, "userprofile", None)

    if not sender_profile or not receiver_profile:
        raise ValidationError("Both users must have profiles before creating sessions.")

    is_cultural = isinstance(target, CulturalConnectionRequest)

    # Decide session type if not provided
    if session_type is None:
        if sender_profile.prefers_online and receiver_profile.prefers_online:
            session_type = "online"
        elif sender_profile.prefers_inperson and receiver_profile.prefers_inperson:
            session_type = "inperson"
        else:
            session_type = "online"

    if session_type not in {"online", "inperson"}:
        raise ValidationError("Session type must be either 'online' or 'inperson'.")

    # Suggested location / platform
    if use_smart_location:
        if session_type == "inperson":
            city = receiver_profile.city or sender_profile.city
            suggested_location = (
                f"Meet at a safe public place in {city}."
                if city
                else "Meet at a safe public place."
            )
        else:
            suggested_location = "Suggested online platform: Zoom / Google Meet / WhatsApp"
    else:
        suggested_location = ""

    created_sessions = []
    skipped_reasons = []

    current_tz = timezone.get_current_timezone()
    now_local = timezone.localtime(timezone.now(), current_tz)

    with transaction.atomic():
        for item in session_dates_times:
            date_str = (item.get("date") or "").strip()
            time_str = (item.get("time") or "").strip()

            if not date_str or not time_str:
                skipped_reasons.append("Missing date or time.")
                continue

            try:
                naive_dt = datetime.strptime(
                    f"{date_str} {time_str}",
                    "%Y-%m-%d %H:%M"
                )
            except ValueError:
                raise ValidationError(
                    f"Invalid date/time combination: {date_str} {time_str}."
                )

            dt_obj = timezone.make_aware(naive_dt, current_tz)
            dt_local = timezone.localtime(dt_obj, current_tz)

            print("RAW DATE:", date_str)
            print("RAW TIME:", time_str)
            print("CURRENT TZ:", current_tz)
            print("NOW LOCAL:", now_local)
            print("SESSION LOCAL:", dt_local)
            print("IS FUTURE:", dt_local > now_local)

            if dt_local <= now_local:
                skipped_reasons.append(
                    f"{date_str} {time_str} is not in the future for timezone {current_tz}."
                )
                continue

            existing_session = Session.objects.filter(
                offer=target.offer if not is_cultural else None,
                cultural_request=target if is_cultural else None,
                date=dt_obj,
            ).first()

            if existing_session:
                created_sessions.append(existing_session)
                continue

            session = Session.objects.create(
                offer=target.offer if not is_cultural else None,
                cultural_request=target if is_cultural else None,
                date=dt_obj,
                type=session_type,
                status="scheduled",
                suggested_location_or_platform=suggested_location,
            )

            SessionParticipant.objects.create(session=session, user=sender)
            SessionParticipant.objects.create(session=session, user=receiver)

            created_sessions.append(session)

    if not created_sessions and skipped_reasons:
        raise ValidationError(" ".join(skipped_reasons))

    return created_sessions