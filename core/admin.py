from django.contrib import admin
from .models import AIConfig, Mission, ChatMessage, LearningProfile, LearningNote, CodeProject, DailyPlan, Quiz, QuizAttempt, AgentNotice, AIUsage, UserProfile
@admin.register(AIConfig)
class AIConfigAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "provider", "model", "is_active", "updated_at")
    exclude = ("encrypted_api_key",)
@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ("title", "skill", "difficulty", "xp", "completed", "created_at")
    list_filter = ("completed", "skill", "difficulty")
@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("role", "created_at")
    readonly_fields = ("role", "content", "created_at")

@admin.register(LearningProfile)
class LearningProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "current_level", "daily_minutes", "updated_at")

@admin.register(LearningNote)
class LearningNoteAdmin(admin.ModelAdmin):
    list_display = ("title", "topic", "updated_at")
    search_fields = ("title", "content", "topic")

@admin.register(CodeProject)
class CodeProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "language", "status", "updated_at")
    list_filter = ("language", "status")

@admin.register(DailyPlan)
class DailyPlanAdmin(admin.ModelAdmin):
    list_display = ("title", "plan_date", "generated_by_ai")

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "topic", "created_at")

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("quiz", "score", "total", "created_at")
    readonly_fields = ("quiz", "answers", "score", "total", "created_at")

@admin.register(AgentNotice)
class AgentNoticeAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "delivered_to_agent", "created_at")
    list_filter = ("kind", "delivered_to_agent")

@admin.register(AIUsage)
class AIUsageAdmin(admin.ModelAdmin):
    list_display = ("user", "day", "calls", "estimated_prompt_chars", "updated_at")
    readonly_fields = ("day", "calls", "estimated_prompt_chars", "updated_at")

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "current_level", "onboarding_complete", "theme", "updated_at")
    list_filter = ("onboarding_complete", "current_level", "theme")
    search_fields = ("user__username", "display_name", "main_goal")
