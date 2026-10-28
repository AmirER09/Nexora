from .models import AIConfig, Mission, UserProfile

def nexora_context(request):
    profile = None
    config = None
    sidebar_skills = []
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={"display_name": user.username})
        config = AIConfig.objects.filter(user=user, is_active=True).first()
        rows = {}
        for mission in Mission.objects.filter(user=user, completed=True):
            rows[mission.skill] = rows.get(mission.skill, 0) + mission.xp
        sidebar_skills = [
            {"name": name, "xp": xp, "level": xp // 100 + 1, "progress": xp % 100}
            for name, xp in sorted(rows.items(), key=lambda item: -item[1])[:3]
        ]
    return {
        "active_ai_config": config,
        "profile": profile,
        "sidebar_skills": sidebar_skills,
        "completed_missions_count": Mission.objects.filter(user=user, completed=True).count() if user and user.is_authenticated else 0,
        "total_missions_count": Mission.objects.filter(user=user).count() if user and user.is_authenticated else 0,
    }
