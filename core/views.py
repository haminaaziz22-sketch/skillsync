from datetime import timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.urls import reverse, reverse_lazy
from .models import CulturalConnectionRequest, MatchRequest, Rating, Session, SessionParticipant, Skill, UserProfile, UserSkill, Offer, Message, create_sessions_from_target, get_cultural_recommendations, get_recommended_matches
from django.contrib.auth.models import User
from .forms import AccountUpdateForm, RescheduleSessionForm, UserProfileForm, UserSkillForm, OfferForm

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden, HttpResponseNotFound, JsonResponse

from django.contrib import messages
from django.utils import timezone



def home(request):
    return render(request, 'home.html')


# ---------------------
# REGISTER
# ---------------------
from .forms import CustomRegisterForm
from django.contrib.auth import login

def register(request):
    if request.method == 'POST':
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomRegisterForm()

    return render(request, 'register.html', {'form': form})



# ---------------------
# DASHBOARD
# ---------------------
@login_required
def dashboard(request):
    user_skills = UserSkill.objects.filter(user=request.user)

    return render(request, 'dashboard.html', {
        'user_skills': user_skills
    })


@login_required
def profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, instance=profile)
        account_form = AccountUpdateForm(request.POST, instance=request.user, user=request.user)

        if profile_form.is_valid() and account_form.is_valid():
            profile_form.save()
            account_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('profile')

        messages.error(request, "Please correct the errors below.")
    else:
        profile_form = UserProfileForm(instance=profile)
        account_form = AccountUpdateForm(instance=request.user, user=request.user)

    user_skills = UserSkill.objects.filter(user=request.user).select_related('skill').order_by('skill__name')

    return render(request, 'profile.html', {
        'profile': profile,
        'form': profile_form,
        'account_form': account_form,
        'user_skills': user_skills
    })

from .forms import CustomPasswordChangeForm
from django.contrib.auth.views import PasswordChangeView

class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'registration/password_change.html'
    form_class = CustomPasswordChangeForm
    success_url = reverse_lazy('profile')

    def form_valid(self, form):
        messages.success(self.request, "Your password was updated successfully.")
        return super().form_valid(form)
    
@login_required
def add_skill(request):
    if request.method == 'POST':
        form = UserSkillForm(request.POST)
        if form.is_valid():
            existing_skill = form.cleaned_data.get("existing_skill")
            new_skill_name = form.cleaned_data.get("new_skill")
            level = form.cleaned_data.get("level")

            if existing_skill:
                skill = existing_skill
            else:
                normalized_name = new_skill_name.strip()
                skill = Skill.objects.filter(name__iexact=normalized_name).first()

                if not skill:
                    skill = Skill.objects.create(
                        name=normalized_name,
                        category="Uncategorized"
                    )

            user_skill, created = UserSkill.objects.get_or_create(
                user=request.user,
                skill=skill,
                defaults={"level": level}
            )

            if created:
                messages.success(request, "Skill added successfully.")
            else:
                if user_skill.level != level:
                    user_skill.level = level
                    user_skill.save()
                    messages.success(request, "Your skill level was updated.")
                else:
                    messages.info(request, "You already have this skill with that level.")

            return redirect('profile')

        messages.error(request, "Please correct the errors below.")
    else:
        form = UserSkillForm()

    return render(request, 'add_skill.html', {
        'form': form
    })

@login_required
def delete_skill(request, skill_id):
    user_skill = get_object_or_404(UserSkill, id=skill_id, user=request.user)
    user_skill.delete()
    messages.success(request, "Skill removed successfully.")
    return redirect('profile')


@login_required
def create_offer(request):
    if request.method == 'POST':
        form = OfferForm(request.POST, user=request.user)
        if form.is_valid():
            offered_skill = form.cleaned_data['offered_skill']
            requested_skill_name = form.cleaned_data['requested_skill_name']

            # Create or get requested skill
            requested_skill, created = Skill.objects.get_or_create(
                name=requested_skill_name,
                defaults={'category': 'Uncategorized'}
            )

            offer = form.save(commit=False)
            offer.creator = request.user
            offer.requested_skill = requested_skill
            offer.status = 'open'  # AUTO SET
            offer.save()

            messages.success(request, "Your offer was created.")
            return redirect('my_offers')

    else:
        form = OfferForm(user=request.user)

    return render(request, 'create_offer.html', {'form': form})



@login_required
def edit_offer(request, offer_id):
    offer = get_object_or_404(Offer, id=offer_id, creator=request.user)

    if request.method == 'POST':
        form = OfferForm(request.POST, instance=offer, user=request.user)
        if form.is_valid():
            requested_skill_name = form.cleaned_data['requested_skill_name'].strip()

            requested_skill, created = Skill.objects.get_or_create(
                name=requested_skill_name,
                defaults={'category': 'Uncategorized'}
            )

            offer = form.save(commit=False)
            offer.requested_skill = requested_skill
            offer.save()

            messages.success(request, "Your offer was updated.")
            return redirect('my_offers')
    else:
        form = OfferForm(
            instance=offer,
            user=request.user,
            initial={
                'requested_skill_name': offer.requested_skill.name if offer.requested_skill else ''
            }
        )

    return render(request, 'edit_offer.html', {
        'form': form,
        'offer': offer
    })

@login_required
def my_offers(request):
    offers = Offer.objects.filter(creator=request.user).prefetch_related("match_requests")

    # Filters
    status = request.GET.get('status')
    skill = request.GET.get('skill')
    category = request.GET.get('category')
    keyword = request.GET.get('keyword')

    if status:
        offers = offers.filter(status=status)

    if skill:
        offers = offers.filter(offered_skill__name__icontains=skill)

    if category:
        offers = offers.filter(offered_skill__category__icontains=category)

    if keyword:
        offers = offers.filter(description__icontains=keyword)

    offers = offers.select_related(
        "offered_skill",
        "requested_skill",
        "matched_user",
    )

    # Attach accepted match request for each offer
    for offer in offers:
        offer.accepted_match_request = offer.match_requests.filter(status="accepted").first()

    return render(request, 'my_offers.html', {'offers': offers})

@login_required
def delete_offer(request, offer_id):
    offer = Offer.objects.get(id=offer_id)

    if offer.creator != request.user:
        return redirect('my_offers')

    offer.delete()
    return redirect('my_offers')


def browse_offers(request):
    offers = Offer.objects.filter(status='open')

    # Logged-in users should not see their own offers here
    if request.user.is_authenticated:
        offers = offers.exclude(creator=request.user)

    # Filters
    status = request.GET.get('status')
    skill = request.GET.get('skill')
    category = request.GET.get('category')
    keyword = request.GET.get('keyword')

    if status:
        offers = offers.filter(status=status)

    if skill:
        offers = offers.filter(offered_skill__name__icontains=skill)

    if category:
        offers = offers.filter(offered_skill__category__icontains=category)

    if keyword:
        offers = offers.filter(description__icontains=keyword)

    # Add helper attributes for template
    if request.user.is_authenticated:
        user_skills = set(
            UserSkill.objects.filter(user=request.user)
            .values_list("skill_id", flat=True)
        )

        sent_request_offer_ids = set(
            MatchRequest.objects.filter(sender=request.user)
            .values_list("offer_id", flat=True)
        )

        for offer in offers:
            offer.user_has_skill = offer.requested_skill_id in user_skills
            offer.user_sent_request = offer.id in sent_request_offer_ids
    else:
        for offer in offers:
            offer.user_has_skill = False
            offer.user_sent_request = False

    return render(request, 'browse_offers.html', {
        'offers': offers
    })

from django.views.decorators.http import require_POST

@login_required
@require_POST
def express_interest(request, offer_id):
    offer = get_object_or_404(Offer, id=offer_id)

    if offer.creator == request.user:
        messages.error(request, "You cannot express interest in your own offer.")
        return redirect('browse_offers')

    try:
        match_request, created = MatchRequest.objects.get_or_create(
            offer=offer,
            sender=request.user,
            receiver=offer.creator,
            defaults={
                'used_smart_matching': False,
            }
        )

        if created:
            messages.success(request, "Request sent successfully.")
        else:
            status_messages = {
                'pending': "You already sent a pending request for this offer.",
                'accepted': "This request has already been accepted.",
                'rejected': "Your previous request for this offer was rejected.",
                'cancelled': "Your previous request for this offer was cancelled.",
            }
            messages.info(
                request,
                status_messages.get(
                    match_request.status,
                    "A request for this offer already exists."
                )
            )

    except ValidationError as e:
        error_messages = []

        if hasattr(e, "message_dict"):
            for field_errors in e.message_dict.values():
                error_messages.extend(field_errors)
        elif hasattr(e, "messages"):
            error_messages.extend(e.messages)
        else:
            error_messages.append("Unable to send request.")

        messages.error(request, " ".join(error_messages))

    return redirect('my_requests')

@login_required
def send_cultural_interest(request, user_id):
    receiver = get_object_or_404(User, id=user_id)

    try:
        cultural_request, created = CulturalConnectionRequest.objects.get_or_create(
            sender=request.user,
            receiver=receiver,
            defaults={
                'initial_message': request.POST.get('initial_message', '').strip()
            }
        )

        if created:
            messages.success(request, "Cultural interest sent successfully.")
        else:
            if cultural_request.status == 'pending':
                messages.info(request, "You already sent a cultural interest request.")
            elif cultural_request.status == 'accepted':
                messages.info(request, "This cultural connection has already been accepted.")
            elif cultural_request.status == 'rejected':
                messages.info(request, "Your previous cultural request was rejected.")
            elif cultural_request.status == 'cancelled':
                messages.info(request, "Your previous cultural request was cancelled.")

    except ValidationError as e:
        if hasattr(e, "message_dict"):
            error_messages = []
            for field_errors in e.message_dict.values():
                error_messages.extend(field_errors)
            messages.error(request, " ".join(error_messages))
        else:
            messages.error(request, " ".join(e.messages))

    return redirect('cultural_discovery')


@login_required
def handle_cultural_request(request, request_id, action):
    req = get_object_or_404(
        CulturalConnectionRequest.objects.select_related('sender', 'receiver'),
        id=request_id
    )

    if req.receiver != request.user:
        messages.error(request, "You are not allowed to handle this request.")
        return redirect('review_requests')

    if req.status != 'pending':
        messages.info(request, "This request has already been handled.")
        return redirect('review_requests')

    if action == 'accept':
        req.status = 'accepted'
        req.save()
        messages.success(request, "Cultural connection request accepted.")

    elif action == 'reject':
        req.status = 'rejected'
        req.save()
        messages.success(request, "Cultural connection request rejected.")

    else:
        messages.error(request, "Invalid action.")

    return redirect('review_requests')

@login_required
def cultural_chat(request, request_id):
    cultural_request = get_object_or_404(CulturalConnectionRequest, id=request_id)

    if request.user not in [cultural_request.sender, cultural_request.receiver]:
        messages.error(request, "You are not allowed to access this chat.")
        return redirect('dashboard')

    if cultural_request.status != 'accepted':
        messages.error(request, "You can only chat after the cultural request is accepted.")
        return redirect('cultural_discovery')

    msgs = Message.objects.filter(
        cultural_request=cultural_request
    ).order_by('timestamp')

    if request.method == 'POST':
        text = request.POST.get('text', '').strip()

        if text:
            receiver = (
                cultural_request.receiver
                if request.user == cultural_request.sender
                else cultural_request.sender
            )

            try:
                Message.objects.create(
                    cultural_request=cultural_request,
                    sender=request.user,
                    receiver=receiver,
                    text=text
                )
            except ValidationError as e:
                if hasattr(e, "message_dict"):
                    error_messages = []
                    for field_errors in e.message_dict.values():
                        error_messages.extend(field_errors)
                    messages.error(request, " ".join(error_messages))
                else:
                    messages.error(request, " ".join(e.messages))

        return redirect('cultural_chat', request_id=request_id)

    return render(request, 'messages.html', {
        'chat_messages': msgs,
        'offer': None,
        'cultural_request': cultural_request,
        'is_cultural': True,
    })

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import MatchRequest


@login_required
def handle_request(request, request_id, action):
    req = get_object_or_404(
        MatchRequest.objects.select_related('offer', 'sender', 'receiver'),
        id=request_id
    )

    if req.receiver != request.user:
        messages.error(request, "You are not allowed to handle this request.")
        return redirect('review_requests')

    if req.status != 'pending':
        messages.info(request, "This request has already been handled.")
        return redirect('review_requests')

    if action == 'accept':
        req.status = 'accepted'
        req.save()

        req.offer.status = 'matched'
        req.offer.matched_user = req.sender
        req.offer.save()

        MatchRequest.objects.filter(
            offer=req.offer,
            status='pending'
        ).exclude(id=req.id).update(status='rejected')

        messages.success(request, "Skill exchange request accepted successfully.")

    elif action == 'reject':
        req.status = 'rejected'
        req.save()
        messages.success(request, "Skill exchange request rejected successfully.")

    else:
        messages.error(request, "Invalid action.")

    return redirect('review_requests')


@login_required
def review_requests(request):
    skill_requests = MatchRequest.objects.filter(
        receiver=request.user,
        status='pending'
    ).select_related(
        'offer',
        'sender',
        'receiver',
        'offer__offered_skill',
        'offer__requested_skill'
    ).order_by('-created_at')

    cultural_requests = CulturalConnectionRequest.objects.filter(
        receiver=request.user,
        status='pending'
    ).select_related(
        'sender',
        'receiver'
    ).order_by('-created_at')

    return render(request, 'review_requests.html', {
        'skill_requests': skill_requests,
        'cultural_requests': cultural_requests
    })

@login_required
def my_requests(request):
    skill_sent = MatchRequest.objects.filter(
        sender=request.user
    ).select_related(
        'offer',
        'receiver',
        'offer__offered_skill',
        'offer__requested_skill'
    ).order_by('-created_at')

    cultural_sent = CulturalConnectionRequest.objects.filter(
        sender=request.user
    ).select_related('receiver').order_by('-created_at')

    return render(request, 'my_requests.html', {
        'skill_sent': skill_sent,
        'cultural_sent': cultural_sent
    })


from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden, HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse


def create_session(request, target_type, target_id):
    if target_type == "match":
        target = get_object_or_404(MatchRequest, id=target_id)
        is_cultural = False
    elif target_type == "cultural":
        target = get_object_or_404(CulturalConnectionRequest, id=target_id)
        is_cultural = True
    else:
        return HttpResponseNotFound("Invalid session target type.")

    if request.user not in {target.sender, target.receiver}:
        return HttpResponseForbidden("You are not allowed to create sessions for this request.")

    if getattr(target, "status", None) != "accepted":
        messages.error(request, "You can only create a session for an accepted request.")
        return redirect("my_cultural_connections" if is_cultural else "my_requests")

    if request.method == "POST":
        dates = request.POST.getlist("date")
        times = request.POST.getlist("time")
        session_type = (request.POST.get("session_type") or "").strip() or None

        session_dates_times = []
        for d, t in zip(dates, times):
            d = (d or "").strip()
            t = (t or "").strip()
            if d and t:
                session_dates_times.append({
                    "date": d,
                    "time": t,
                })

        print("RAW DATES:", dates)
        print("RAW TIMES:", times)
        print("SESSION DATE/TIMES:", session_dates_times)
        print("SESSION TYPE:", session_type)
        print("TARGET STATUS:", getattr(target, "status", None))
        print("TARGET TYPE:", target_type)
        print("REQUEST USER:", request.user.username)

        if not session_dates_times:
            messages.error(request, "Please provide at least one valid date and time.")
            return redirect(request.path)

        try:
            sessions = create_sessions_from_target(
                target=target,
                session_dates_times=session_dates_times,
                session_type=session_type,
                use_smart_location=True,
            )

            print("SESSIONS RETURNED:", sessions)
            print("SESSIONS COUNT:", len(sessions) if sessions else 0)

        except ValidationError as e:
            print("VALIDATION ERROR:", e)

            if hasattr(e, "message_dict"):
                print("VALIDATION ERROR DICT:", e.message_dict)
                error_messages = []
                for field_errors in e.message_dict.values():
                    error_messages.extend(field_errors)
                messages.error(request, " ".join(error_messages))
            elif hasattr(e, "messages"):
                print("VALIDATION ERROR MESSAGES:", e.messages)
                messages.error(request, " ".join(e.messages))
            else:
                messages.error(request, str(e))

            return redirect(request.path)

        except Exception as e:
            print("GENERAL ERROR:", repr(e))
            messages.error(request, f"Session creation failed: {e}")
            return redirect(request.path)

        if not sessions:
            messages.error(
                request,
                "No sessions were created. The selected date/time may be in the past, or the session details may not be valid."
            )
            return redirect(request.path)

        messages.success(request, f"{len(sessions)} session(s) created successfully.")
        return redirect("my_sessions")

    session_with = target.receiver if request.user == target.sender else target.sender
    cancel_url = reverse("my_cultural_connections" if is_cultural else "my_requests")

    return render(request, "create_session.html", {
        "target": target,
        "is_cultural": is_cultural,
        "session_with": session_with,
        "cancel_url": cancel_url,
    })



@login_required
def session_detail(request, session_id):
    session = get_object_or_404(
        Session.objects.select_related(
            'offer',
            'offer__creator',
            'offer__matched_user',
            'cultural_request',
            'cultural_request__sender',
            'cultural_request__receiver',
        ),
        id=session_id
    )

    is_participant = SessionParticipant.objects.filter(
        session=session,
        user=request.user
    ).exists()

    if not is_participant:
        messages.error(request, "You are not allowed to view this session.")
        return redirect('dashboard')

    participants = SessionParticipant.objects.filter(
        session=session
    ).select_related('user')

    return render(request, 'session_detail.html', {
        'session': session,
        'participants': participants,
        'now': timezone.now(),
    })


@login_required
def my_sessions(request):
    sessions = Session.objects.filter(
        sessionparticipant__user=request.user
    ).select_related(
        'offer',
        'offer__creator',
        'offer__matched_user'
    ).distinct().order_by('date')

    return render(request, 'my_sessions.html', {
        'sessions': sessions
    })


@login_required
def cancel_session(request, session_id):
    session = get_object_or_404(Session, id=session_id)

    is_participant = SessionParticipant.objects.filter(
        session=session,
        user=request.user
    ).exists()

    if not is_participant:
        messages.error(request, "You are not a participant in this session.")
        return redirect('my_sessions')

    if session.status != 'scheduled':
        messages.error(request, "Only scheduled sessions can be cancelled.")
        return redirect('my_sessions')

    if timezone.now() > session.date - timedelta(hours=4):
        messages.error(request, "Cannot cancel less than 4 hours before the session.")
        return redirect('my_sessions')

    session.status = 'cancelled'
    session.save()

    messages.success(request, "Session cancelled successfully.")
    return redirect('my_sessions')


@login_required
def reschedule_session(request, session_id):
    session = get_object_or_404(Session, id=session_id)

    is_participant = SessionParticipant.objects.filter(
        session=session,
        user=request.user
    ).exists()

    if not is_participant:
        messages.error(request, "You are not a participant in this session.")
        return redirect('my_sessions')

    if session.status != 'scheduled':
        messages.error(request, "Only scheduled sessions can be rescheduled.")
        return redirect('my_sessions')

    if request.method == 'POST':
        form = RescheduleSessionForm(request.POST, instance=session)

        if form.is_valid():
            form.save()
            messages.success(request, "Session rescheduled successfully.")
            return redirect('my_sessions')
        else:
            messages.error(request, "Invalid data. Please correct the form.")
    else:
        form = RescheduleSessionForm(instance=session)

    date_value = session.date.astimezone(
        timezone.get_current_timezone()
    ).strftime('%Y-%m-%dT%H:%M')

    other_participant = (
        SessionParticipant.objects
        .filter(session=session)
        .exclude(user=request.user)
        .select_related('user')
        .first()
    )
    session_with = other_participant.user if other_participant else None

    is_cultural = bool(session.cultural_request)

    cancel_url = reverse('session_detail', kwargs={'session_id': session.id})

    suggested_location_preview = (
        session.suggested_location_or_platform
        or "Will remain based on the session setup."
    )

    return render(request, 'create_session.html', {
        'form': form,
        'session': session,
        'offer': session.offer,
        'cultural_request': session.cultural_request,
        'session_with': session_with,
        'suggested_type': session.get_type_display() if session.type else None,
        'suggested_location_preview': suggested_location_preview,
        'is_cultural': is_cultural,
        'is_reschedule': True,
        'date_value': date_value,
        'type_value': session.type,
        'cancel_url': cancel_url,
    })


@login_required
def complete_session(request, session_id):
    session = get_object_or_404(Session, id=session_id)

    is_participant = SessionParticipant.objects.filter(
        session=session,
        user=request.user
    ).exists()

    if not is_participant:
        messages.error(request, "You are not allowed to complete this session.")
        return redirect('dashboard')

    if session.status != 'scheduled':
        messages.error(request, "Only scheduled sessions can be marked as completed.")
        return redirect('session_detail', session_id=session.id)

    if session.date > timezone.now():
        messages.error(request, "You cannot complete this session yet. The scheduled time has not arrived.")
        return redirect('session_detail', session_id=session.id)

    session.status = 'completed'
    session.save()

    messages.success(request, "Session marked as completed.")
    return redirect('session_detail', session_id=session.id)


@login_required
def rate_user(request, session_id, receiver_id):
    session = get_object_or_404(Session, id=session_id)
    receiver = get_object_or_404(User, id=receiver_id)

    # Session must be completed
    if session.status != 'completed':
        messages.error(request, "You can only rate users after the session is completed.")
        return redirect('session_detail', session_id=session_id)

    # Both users must be participants in this session
    participant_ids = set(
        SessionParticipant.objects.filter(session=session).values_list('user_id', flat=True)
    )

    if request.user.id not in participant_ids or receiver.id not in participant_ids:
        messages.error(request, "Both users must be participants in this session.")
        return redirect('session_detail', session_id=session_id)

    # Cannot rate yourself
    if request.user.id == receiver.id:
        messages.error(request, "You cannot rate yourself.")
        return redirect('session_detail', session_id=session_id)

    existing_rating = Rating.objects.filter(
        giver=request.user,
        receiver=receiver
    ).first()

    if request.method == 'POST':
        score = request.POST.get('score')
        comment = request.POST.get('comment', '').strip()

        try:
            if existing_rating:
                existing_rating.score = score
                existing_rating.comment = comment
                existing_rating.save()
                messages.success(request, "Rating updated successfully.")
            else:
                Rating.objects.create(
                    score=score,
                    comment=comment,
                    giver=request.user,
                    receiver=receiver
                )
                messages.success(request, "Rating submitted successfully.")

            return redirect('session_detail', session_id=session_id)

        except ValidationError as e:
            if hasattr(e, "message_dict"):
                error_messages = []
                for field_errors in e.message_dict.values():
                    error_messages.extend(field_errors)
                messages.error(request, " ".join(error_messages))
            else:
                messages.error(request, " ".join(e.messages))

    return render(request, 'rate_user.html', {
        'session': session,
        'receiver': receiver,
        'existing_rating': existing_rating,
    })



@login_required
def recommended_matches(request):
    user_profile = getattr(request.user, 'userprofile', None)

    if not user_profile:
        messages.error(request, "Please complete your profile first.")
        return redirect('profile')

    if not user_profile.enable_smart_matching:
        messages.info(
            request,
            "Turn on smart matching in your profile to see personalized recommendations."
        )
        return render(request, 'recommended.html', {
            'recs': [],
            'has_results': False,
            'smart_matching_enabled': False,
        })

    recs = get_recommended_matches(request.user, use_smart=True)

    for rec in recs:
        existing_request = MatchRequest.objects.filter(
            offer=rec['offer'],
            sender=request.user,
            receiver=rec['creator']
        ).first()

        rec['existing_request'] = existing_request
        rec['request_status'] = existing_request.status if existing_request else None

        score = rec['score']
        if score >= 80:
            rec['match_label'] = "Excellent match"
        elif score >= 65:
            rec['match_label'] = "Good match"
        else:
            rec['match_label'] = "Possible match"

    return render(request, 'recommended.html', {
        'recs': recs,
        'has_results': bool(recs),
        'smart_matching_enabled': True,
    })

from django.db.models import Q

@login_required
def cultural_discovery(request):
    profile = getattr(request.user, 'userprofile', None)

    if not profile:
        messages.error(request, "Please complete your profile first.")
        return redirect('profile')

    if not profile.interested_in_cultural_exchange:
        messages.info(
            request,
            "Turn on cultural discovery in your profile to explore cultural skill matches."
        )
        return render(request, 'cultural.html', {
            'matches': [],
            'has_results': False,
            'cultural_enabled': False,
        })

    matches = get_cultural_recommendations(request.user)

    for match in matches:
        existing_request = CulturalConnectionRequest.objects.filter(
            Q(sender=request.user, receiver=match['user']) |
            Q(sender=match['user'], receiver=request.user)
        ).select_related('sender', 'receiver').order_by('-created_at').first()

        match['existing_request'] = existing_request
        match['request_status'] = existing_request.status if existing_request else None

        if existing_request:
            if existing_request.sender == request.user:
                match['request_direction'] = 'sent'
            else:
                match['request_direction'] = 'received'
        else:
            match['request_direction'] = None

    return render(request, 'cultural.html', {
        'matches': matches,
        'has_results': bool(matches),
        'cultural_enabled': True,
    })

@login_required
def my_cultural_connections(request):
    connections = CulturalConnectionRequest.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user),
        status='accepted'
    ).select_related('sender', 'receiver').order_by('-created_at')

    return render(request, 'my_cultural_connections.html', {
        'connections': connections
    })

@login_required
def chat_messages(request, target_id):
    offer = Offer.objects.filter(id=target_id).first()
    cultural_request = CulturalConnectionRequest.objects.filter(id=target_id).first()

    if not offer and not cultural_request:
        messages.error(request, "Chat not found.")
        return redirect("dashboard")

    is_cultural = cultural_request is not None

    if is_cultural:
        allowed_users = [cultural_request.sender, cultural_request.receiver]
    else:
        if offer.matched_user is None:
            messages.error(request, "This offer does not have an active chat yet.")
            return redirect("my_requests")
        allowed_users = [offer.creator, offer.matched_user]

    if request.user not in allowed_users:
        messages.error(request, "You are not allowed to access this chat.")
        return redirect("dashboard")

    if is_cultural:
        msgs = Message.objects.filter(cultural_request=cultural_request).order_by("timestamp")
        receiver = cultural_request.sender if request.user != cultural_request.sender else cultural_request.receiver
    else:
        msgs = Message.objects.filter(offer=offer).order_by("timestamp")
        receiver = offer.creator if request.user != offer.creator else offer.matched_user

    if request.method == "POST":
        text = request.POST.get("text", "").strip()

        if text:
            try:
                Message.objects.create(
                    offer=offer if not is_cultural else None,
                    cultural_request=cultural_request if is_cultural else None,
                    sender=request.user,
                    receiver=receiver,
                    text=text
                )
            except ValidationError as e:
                if hasattr(e, "message_dict"):
                    error_messages = []
                    for field_errors in e.message_dict.values():
                        error_messages.extend(field_errors)
                    messages.error(request, " ".join(error_messages))
                else:
                    messages.error(request, " ".join(e.messages))

        return redirect("chat_messages", target_id=target_id)

    return render(request, "messages.html", {
        "chat_messages": msgs,
        "offer": offer,
        "cultural_request": cultural_request,
        "is_cultural": is_cultural,
    })

@login_required
def fetch_messages(request, target_id):
    offer = Offer.objects.filter(id=target_id).first()
    cultural_request = CulturalConnectionRequest.objects.filter(id=target_id).first()

    if not offer and not cultural_request:
        return JsonResponse({'error': 'Chat not found.'}, status=404)

    is_cultural = cultural_request is not None

    if is_cultural:
        allowed_users = [cultural_request.sender, cultural_request.receiver]
    else:
        allowed_users = [offer.creator, offer.matched_user]

    if request.user not in allowed_users:
        return JsonResponse({'error': 'Not allowed'}, status=403)

    if not is_cultural and offer.matched_user is None:
        return JsonResponse({'error': 'This offer does not have an active chat yet.'}, status=400)

    if is_cultural:
        msgs = Message.objects.filter(cultural_request=cultural_request).order_by('timestamp')
    else:
        msgs = Message.objects.filter(offer=offer).order_by('timestamp')

    data = [
        {
            'id': m.id,
            'sender': m.sender.username,
            'is_own': m.sender_id == request.user.id,
            'text': m.text,
            'timestamp': m.timestamp.strftime("%I:%M %p").lstrip("0")
        }
        for m in msgs
    ]

    return JsonResponse({'messages': data})