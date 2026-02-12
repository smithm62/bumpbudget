from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import *
from django.contrib.auth import login
from .forms import *
from decimal import Decimal


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
