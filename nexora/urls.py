from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("onboarding/", views.onboarding, name="onboarding"),
    path("settings/theme/", views.save_theme, name="save_theme"),
    path("admin/", admin.site.urls),
    path("", views.dashboard, name="dashboard"),
    path("mentor/", views.mentor, name="mentor"),
    path("settings/", views.settings_page, name="settings"),
    path("settings/test/", views.test_api, name="test_api"),
    path("api/chat/", views.chat_api, name="chat_api"),
    path("api/mission/new/", views.new_mission, name="new_mission"),
    path("api/mission/auto/", views.auto_mission, name="auto_mission"),
    path("api/mission/<int:mission_id>/delete/", views.delete_mission, name="delete_mission"),
    path("api/mission/complete/", views.complete_mission, name="complete_mission"),
    path("learning/", views.learning_hub, name="learning_hub"),
    path("learning/interests/update/", views.update_interests, name="update_interests"),
    path("portfolio/", views.portfolio, name="portfolio"),
    path("learning/plan/generate/", views.generate_daily_plan, name="generate_daily_plan"),
    path("learning/path/generate/", views.generate_learning_path, name="generate_learning_path"),
    path("learning/path/<int:path_id>/step/<str:step_id>/toggle/", views.toggle_learning_step, name="toggle_learning_step"),
    path("learning/notes/save/", views.save_note, name="save_note"),
    path("learning/notes/<int:note_id>/delete/", views.delete_note, name="delete_note"),
    path("learning/projects/save/", views.save_project, name="save_project"),
    path("learning/projects/<int:project_id>/delete/", views.delete_project, name="delete_project"),
    path("learning/quizzes/create/", views.generate_quiz, name="generate_quiz"),
    path("learning/quizzes/<int:quiz_id>/", views.quiz_detail, name="quiz_detail"),
    path("learning/quizzes/<int:quiz_id>/submit/", views.submit_quiz, name="submit_quiz"),
]
