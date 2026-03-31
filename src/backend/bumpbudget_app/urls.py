from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("faq/", views.faq, name="faq"),
    path("contact/", views.contact, name="contact"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),
    path("setup/", views.profile_setup, name="profile_setup"),
    path("profile/", views.profile, name="profile"),
    path("goals/", views.goals, name="goals"),
    path("goals/toggle/<int:goal_id>/", views.toggle_goal, name="toggle_goal"),
    path("goals/add-savings/", views.add_savings, name="add_savings"),
    path("resources/", views.resources, name="resources"),
    path("tracker/", views.tracker, name="tracker"),
    path("timeline/", views.timeline, name="timeline"),
    path("plan/", views.plan, name="plan"),
    # Expenses
    path("expenses/", views.expense_list, name="expense_list"),
    path("expenses/add/", views.add_expense, name="add_expense"),
    path("expenses/<int:pk>/edit/", views.edit_expense, name="edit_expense"),
    path("expenses/<int:pk>/delete/", views.delete_expense, name="delete_expense"),
    # Savings goals
    path("savings/", views.savings_goals, name="savings_goals"),
    path("savings/add/", views.add_savings_goal, name="add_savings_goal"),
    path("savings/<int:pk>/edit/", views.edit_savings_goal, name="edit_savings_goal"),
    path("savings/<int:pk>/delete/", views.delete_savings_goal, name="delete_savings_goal"),
    path("savings/log/<int:pk>/", views.log_to_goal, name="log_to_goal"),
    # Community
    path("community/", views.community, name="community"),
    path("community/new/", views.create_post, name="create_post"),
    path("community/<int:pk>/", views.post_detail, name="post_detail"),
    path("community/<int:pk>/edit/", views.edit_post, name="edit_post"),
    path("community/<int:pk>/delete/", views.delete_post, name="delete_post"),
    path("community/<int:pk>/like/", views.toggle_like, name="toggle_like"),
    path("community/<int:pk>/pin/", views.pin_post, name="pin_post"),
    path("community/<int:pk>/remove/", views.remove_post, name="remove_post"),
    path("community/reply/<int:pk>/edit/", views.edit_reply, name="edit_reply"),
    path("community/reply/<int:pk>/delete/", views.delete_reply, name="delete_reply"),
    path("community/reply/<int:pk>/remove/", views.remove_reply, name="remove_reply"),
    # Staff
    path("staff/", views.staff_dashboard, name="staff_dashboard"),
    path("staff/user/<int:user_id>/toggle-role/", views.staff_toggle_role, name="staff_toggle_role"),
    path("staff/user/<int:user_id>/delete/", views.staff_delete_user, name="staff_delete_user"),
    # Messaging
    path('inbox/', views.inbox, name='inbox'),
    path('inbox/<int:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    path('message/<int:user_id>/', views.start_conversation, name='start_conversation'),
]