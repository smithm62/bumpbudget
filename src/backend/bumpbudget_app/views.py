from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import *
from django.contrib.auth import login
from .forms import *
from decimal import Decimal
from datetime import date
from .models import UserProfile


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("profile_setup")
    else:
        form = RegisterForm()

    return render(request, "register.html", {"form": form})

def home(request):
    return render(request, "home.html")

def faq(request):
    return render(request, "faq.html")

def contact(request):
    return render(request, "contact.html")

def dashboard(request):
    return render(request, "dashboard.html")

def budget(request):
    return render(request, "budget.html")

def goals(request):
    return render(request, "goals.html")

def resources(request):
    return render(request, "resources.html")

def tracker(request):
    return render(request, "tracker.html")

def timeline(request):
    return render(request, "timeline.html")

from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from .models import UserProfile


@login_required
def dashboard(request):
    profile = UserProfile.objects.filter(user=request.user).first()

    if not profile:
        return redirect("profile_setup")

    # Always require monthly income (core to dashboard math)
    if profile.monthly_income is None:
        return redirect("profile_setup")

    # Stage-specific requirements
    if profile.life_stage == UserProfile.LifeStage.EXPECTING:
        if not profile.due_date:
            return redirect("profile_setup")

    elif profile.life_stage == UserProfile.LifeStage.EARLY:
        if profile.child_age_months is None:
            return redirect("profile_setup")

    # PLANNING: no extra required fields (by design)

    partner_income = profile.partner_monthly_income or Decimal("0.00")
    monthly_income = profile.monthly_income + partner_income

    # Temporary placeholder until Expense models exist
    total_expenses = Decimal("1950.00")
    remaining = monthly_income - total_expenses

    context = {
        "profile": profile,
        "monthly_income": monthly_income,
        "total_expenses": total_expenses,
        "remaining": remaining,
    }
    return render(request, "dashboard.html", context)


    
@login_required
def profile_setup(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = ProfileSetupForm(request.POST, instance=profile)
        if form.is_valid():
            prof = form.save(commit=False)
            prof.user = request.user
            prof.save()
            return redirect("dashboard")
    else:
        form = ProfileSetupForm(instance=profile)

    return render(request, "profile_setup.html", {"form": form})

@login_required
def timeline(request):

    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    today = date.today()

    if profile.due_date:
        days_until_due = (profile.due_date - today).days
        current_week = 40 - (days_until_due // 7)
        progress_percent = (current_week / 40) * 100
        current_month = min(max(current_week // 4, 1), 9)

        remaining_weeks = 40 - current_week

    else:
        current_week = 0
        progress_percent = 0
        current_month = 1


    timeline_data = [
        {
            "month": 1,
            "icon": "images/month_icons/discovery.png",
            "icon_type": "horizontal",
            "tasks": ["Take pregnancy test", "Book GP appointment"]
        },
        {
            "month": 2,
            "icon": "images/month_icons/doctor.png",
            "icon_type": "horizontal",
            "tasks": ["First prenatal visit", "Start prenatal vitamins"]
        },
        {
            "month": 3,
            "icon": "images/month_icons/ultrasound.png",
            "icon_type": "horizontal",
            "tasks": ["First ultrasound", "Tell close family"]
        },
        {
            "month": 4,
            "icon": "images/month_icons/notebook.png",
            "icon_type": "vertical",
            "tasks": ["Anatomy scan", "Start thinking about baby names"]
        },
        {
            "month": 5,
            "icon": "images/month_icons/balloons.png",
            "icon_type": "vertical",
            "tasks": ["Gender reveal", "Start baby registry"]
        },
        {
            "month": 6,
            "icon": "images/month_icons/nursery.png",
            "icon_type": "horizontal",
            "tasks": ["Buy baby clothes", "Plan nursery", "Research childcare"]
        },
        {
            "month": 7,
            "icon": "images/month_icons/hospitalbag.png",
            "icon_type": "vertical",
            "tasks": ["Pack hospital bag", "Prenatal classes"]
        },
        {
            "month": 8,
            "icon": "images/month_icons/carseat.png",
            "icon_type": "vertical",
            "tasks": ["Install car seat", "Finalize hospital plan"]
        },
        {
            "month": 9,
            "icon": "images/month_icons/babyborn.png",
            "icon_type": "vertical",
            "tasks": ["Prepare hospital documents", "Rest and prepare"]
        },
    ]

    remaining_months = [
        m for m in timeline_data if m["month"] >= current_month
    ]


    baby_sizes = {
        8: "raspberry",
        12: "lime",
        16: "avocado",
        20: "banana",
        24: "corn",
        28: "eggplant",
        32: "coconut",
        36: "papaya",
        40: "watermelon"
    }

    baby_size = None

    for week in sorted(baby_sizes):
        if current_week >= week:
            baby_size = baby_sizes[week]

    baby_image = f"images/baby_sizes/{baby_size}.png"

    context = {
        "profile": profile,
        "current_week": current_week,
        "remaining_weeks": remaining_weeks,
        "progress_percent": progress_percent,
        "current_month": current_month,
        "timeline": remaining_months,
        "baby_size": baby_size,
        "baby_image": baby_image,
    }
    
    return render(request, "timeline.html", context)