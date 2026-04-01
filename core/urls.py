from django.urls import path
from . import views

urlpatterns = [
    # Home + Auth
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),

    # Dashboard + Skills
    path('dashboard/', views.dashboard, name='dashboard'),
    path('add-skill/', views.add_skill, name='add_skill'),
    path('delete-skill/<int:skill_id>/', views.delete_skill, name='delete_skill'),
    path('cultural/', views.cultural_discovery, name='cultural_discovery'),
    path('category-recommendations/', views.category_recommendations, name='category_recommendations'),



    # Offers
    path('create-offer/', views.create_offer, name='create_offer'),
    path('offers/', views.browse_offers, name='browse_offers'),
    path('my-offers/', views.my_offers, name='my_offers'),
    path('delete-offer/<int:offer_id>/', views.delete_offer, name='delete_offer'),

    # Matching
    path('express-interest/<int:offer_id>/', views.express_interest, name='express_interest'),
    path('review-requests/', views.review_requests, name='review_requests'),
    path('my-requests/', views.my_requests, name='my_requests'),
    path('handle-request/<int:request_id>/<str:action>/', views.handle_request, name='handle_request'),
    path('recommended/', views.recommended_matches, name='recommended_matches'),


    # Messaging
    path('chat_messages/<int:offer_id>/', views.chat_messages, name='chat_messages'),
    path('fetch_messages/<int:offer_id>/', views.fetch_messages, name='fetch_messages'),


    # Sessions
    path('create-session/<int:offer_id>/', views.create_session, name='create_session'),
    path('session/<int:session_id>/', views.session_detail, name='session_detail'),
    path('my-sessions/', views.my_sessions, name='my_sessions'),
    path('cancel-session/<int:session_id>/', views.cancel_session, name='cancel_session'),
    path('reschedule-session/<int:session_id>/', views.reschedule_session, name='reschedule_session'),
    path('complete-session/<int:session_id>/', views.complete_session, name='complete_session'),

    # Ratings
    path('rate/<int:session_id>/<int:receiver_id>/', views.rate_user, name='rate_user'),
]
