from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .models import MatchRequest, Rating, Session, SessionParticipant, Skill, UserProfile, UserSkill, Offer, Message, get_cultural_recommendations, get_recommended_matches
from django.contrib.auth.models import User
from .forms import RescheduleSessionForm, UserProfileForm, UserSkillForm, OfferForm



def home(request):
    return render(request, 'core/home.html')


# ---------------------
# REGISTER
# ---------------------
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()

    return render(request, 'registration/register.html', {'form': form})



# ---------------------
# DASHBOARD
# ---------------------
@login_required
def dashboard(request):
    user_skills = UserSkill.objects.filter(user=request.user)

    return render(request, 'core/dashboard.html', {
        'user_skills': user_skills
    })


@login_required
def profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)

    return render(request, 'core/profile.html', {
        'profile': profile,
        'form': form
    })
# ---------------------
# ADD SKILL
# ---------------------
@login_required
def add_skill(request):
    if request.method == 'POST':
        form = UserSkillForm(request.POST)
        if form.is_valid():
            existing_skill = form.cleaned_data.get("existing_skill")
            new_skill_name = form.cleaned_data.get("new_skill")

            # Case 1: User selected an existing skill
            if existing_skill:
                skill = existing_skill

            # Case 2: User typed a new skill
            else:
                skill, created = Skill.objects.get_or_create(
                    name=new_skill_name,
                    defaults={"category": "Uncategorized"}
                )

            # Try to link skill to user
            user_skill, created = UserSkill.objects.get_or_create(
                user=request.user,
                skill=skill
            )

            if not created:
                messages.warning(request, "You already have this skill.")
            else:
                messages.success(request, "Skill added successfully!")

            return redirect('dashboard')

    else:
        form = UserSkillForm()

    return render(request, 'core/add_skill.html', {'form': form})



# ---------------------
# DELETE SKILL
# ---------------------
@login_required
def delete_skill(request, skill_id):
    user_skill = UserSkill.objects.get(id=skill_id, user=request.user)
    user_skill.delete()
    return redirect('dashboard')



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

            return redirect('my_offers')

    else:
        form = OfferForm(user=request.user)

    return render(request, 'core/create_offer.html', {'form': form})


@login_required
def my_offers(request):
    offers = Offer.objects.filter(creator=request.user)

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

    return render(request, 'core/my_offers.html', {'offers': offers})

@login_required
def delete_offer(request, offer_id):
    offer = Offer.objects.get(id=offer_id)

    if offer.creator != request.user:
        return redirect('my_offers')

    offer.delete()
    return redirect('my_offers')


def browse_offers(request):
    offers = Offer.objects.filter(status='open')

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

        for offer in offers:
            offer.user_has_skill = offer.requested_skill_id in user_skills
            offer.user_sent_request = MatchRequest.objects.filter(
                offer=offer, sender=request.user
            ).exists()
    else:
        for offer in offers:
            offer.user_has_skill = False
            offer.user_sent_request = False

    return render(request, 'core/browse_offers.html', {
        'offers': offers
    })

from django.contrib import messages

@login_required
def express_interest(request, offer_id):
    offer = Offer.objects.get(id=offer_id)

    if offer.creator == request.user:
        messages.error(request, "You cannot request your own offer.")
        return redirect('browse_offers')

    has_skill = UserSkill.objects.filter(
        user=request.user,
        skill=offer.requested_skill
    ).exists()

    if not has_skill:
        messages.error(request, "You do not have the required skill.")
        return redirect('browse_offers')

    MatchRequest.objects.get_or_create(
        offer=offer,
        sender=request.user,
        receiver=offer.creator
    )

    messages.success(request, "Request sent successfully!")
    return redirect('browse_offers')

@login_required
def review_requests(request):
    requests = MatchRequest.objects.filter(receiver=request.user, status='pending')
    return render(request, 'core/review_requests.html', {'requests': requests})

@login_required
def my_requests(request):
    sent = MatchRequest.objects.filter(sender=request.user)
    return render(request, 'core/my_requests.html', {'sent': sent})

@login_required
def handle_request(request, request_id, action):
    req = MatchRequest.objects.get(id=request_id)

    # Only the receiver (offer creator) can act
    if req.receiver != request.user:
        return redirect('review_requests')

    if action == 'accept':
        req.status = 'accepted'
        req.offer.status = 'matched'
        req.offer.matched_user = req.sender
        req.offer.save()
    else:
        req.status = 'rejected'

    req.save()
    return redirect('review_requests')

@login_required
def chat_messages(request, offer_id):
    offer = Offer.objects.get(id=offer_id)

    # Only matched users can message
    if request.user not in [offer.creator, offer.matched_user]:
        return redirect('dashboard')

    msgs = Message.objects.filter(offer=offer).order_by('timestamp')

    if request.method == 'POST':
        Message.objects.create(
            offer=offer,
            sender=request.user,
            receiver=offer.creator if request.user != offer.creator else offer.matched_user,
            text=request.POST['text']
        )
        return redirect('chat_messages', offer_id=offer_id)

    return render(request, 'core/messages.html', {'messages': msgs, 'offer': offer})

@login_required
def create_session(request, offer_id):
    offer = Offer.objects.get(id=offer_id)

    if request.user not in [offer.creator, offer.matched_user]:
        return redirect('dashboard')

    if request.method == 'POST':
        session = Session.objects.create(
            offer=offer,
            date=request.POST['date'],
            type=request.POST['type'],
            status='scheduled'
        )

        # Add both participants
        SessionParticipant.objects.create(session=session, user=offer.creator)
        SessionParticipant.objects.create(session=session, user=offer.matched_user)

        return redirect('session_detail', session_id=session.id)

    return render(request, 'core/create_session.html', {'offer': offer})

from django.utils import timezone

@login_required
def session_detail(request, session_id):
    session = Session.objects.get(id=session_id)

    participants = session.sessionparticipant_set.values_list('user', flat=True)
    if request.user.id not in participants:
        return redirect('dashboard')

    return render(request, 'core/session_detail.html', {
        'session': session,
        'now': timezone.now()
    })


@login_required
def my_sessions(request):
    sessions = Session.objects.filter(
        sessionparticipant__user=request.user
    ).order_by('date')

    return render(request, 'core/my_sessions.html', {
        'sessions': sessions
    })
from django.utils import timezone
from datetime import timedelta

@login_required
def cancel_session(request, session_id):
    session = Session.objects.get(id=session_id)

    if not SessionParticipant.objects.filter(session=session, user=request.user).exists():
        return redirect('my_sessions')

    if session.status != 'scheduled':
        return redirect('my_sessions')

    # Must be at least 4 hours before
    if timezone.now() > session.date - timedelta(hours=4):
        return redirect('my_sessions')

    session.status = 'cancelled'
    session.save()

    return redirect('my_sessions')


@login_required
def reschedule_session(request, session_id):
    session = Session.objects.get(id=session_id)

    # Only participants can reschedule
    if not SessionParticipant.objects.filter(session=session, user=request.user).exists():
        return redirect('my_sessions')

    if session.status != 'scheduled':
        return redirect('my_sessions')

    if request.method == 'POST':
        form = RescheduleSessionForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            return redirect('my_sessions')
    else:
        form = RescheduleSessionForm(instance=session)

    return render(request, 'core/reschedule_session.html', {
        'form': form,
        'session': session
    })



@login_required
def complete_session(request, session_id):
    session = Session.objects.get(id=session_id)

    if request.user not in session.sessionparticipant_set.values_list('user', flat=True):
        return redirect('dashboard')

    session.status = 'completed'
    session.save()

    return redirect('session_detail', session_id=session_id)

@login_required
def rate_user(request, session_id, receiver_id):
    session = Session.objects.get(id=session_id)
    receiver = User.objects.get(id=receiver_id)

    # Must be completed
    if session.status != 'completed':
        return redirect('session_detail', session_id=session_id)

    # Must be a participant
    participants = SessionParticipant.objects.filter(session=session).values_list('user', flat=True)
    if request.user.id not in participants or receiver.id not in participants:
        return redirect('session_detail', session_id=session_id)

    # Cannot rate yourself
    if request.user.id == receiver.id:
        return redirect('session_detail', session_id=session_id)

    # Prevent duplicate rating
    if Rating.objects.filter(session=session, giver=request.user, receiver=receiver).exists():
        return redirect('session_detail', session_id=session_id)

    if request.method == 'POST':
        Rating.objects.create(
            score=request.POST['score'],
            comment=request.POST['comment'],
            session=session,
            giver=request.user,
            receiver=receiver
        )
        return redirect('session_detail', session_id=session_id)

    return render(request, 'core/rate_user.html', {
        'session': session,
        'receiver': receiver
    })



@login_required
def recommended_matches(request):
    recs = get_recommended_matches(request.user)
    return render(request, 'core/recommended.html', {'recs': recs})

@login_required
def cultural_discovery(request):
    offers = get_cultural_recommendations(request.user)
    return render(request, 'core/cultural.html', {'offers': offers})

from .models import get_category_recommendations

@login_required
def category_recommendations(request):
    offers = get_category_recommendations(request.user)
    return render(request, 'core/category_recommendations.html', {
        'offers': offers
    })
from django.http import JsonResponse

@login_required
def fetch_messages(request, offer_id):
    offer = Offer.objects.get(id=offer_id)

    if request.user not in [offer.creator, offer.matched_user]:
        return JsonResponse({'error': 'Not allowed'}, status=403)

    msgs = Message.objects.filter(offer=offer).order_by('timestamp')

    data = [
        {
            'sender': m.sender.username,
            'text': m.text,
            'timestamp': m.timestamp.strftime("%Y-%m-%d %H:%M")
        }
        for m in msgs
    ]

    return JsonResponse({'messages': data})
