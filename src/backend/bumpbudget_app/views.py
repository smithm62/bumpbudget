import json
import math
from decimal import Decimal
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, DecimalField
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import *
from .models import *


# ---------------------------------------------------------------------------
# Public views
# ---------------------------------------------------------------------------

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

@login_required
def plan(request):
    from .ml_advisor import get_recommendation
    profile = UserProfile.objects.filter(user=request.user).first()
    if not profile:
        return redirect("profile_setup")

    ml = None
    if profile.monthly_income:
        partner_income = profile.partner_monthly_income or Decimal("0.00")
        monthly_income = float(profile.monthly_income + partner_income)
        if profile.due_date:
            days_left = (profile.due_date - date.today()).days
            months_remaining = max(days_left // 30, 1)
        else:
            months_remaining = 8
        ml = get_recommendation(monthly_income, months_remaining)

    return render(request, "plan.html", {"ml": ml, "profile": profile})

def contact(request):
    return render(request, "contact.html")

def resources(request):
    return render(request, "resources.html")


# ---------------------------------------------------------------------------
# Helper: category spend vs limits
# ---------------------------------------------------------------------------

def _category_budget_data(user, month_start):
    actuals = {
        row["category"]: row["total"]
        for row in (
            Expense.objects
            .filter(user=user, date__gte=month_start, is_upcoming=False)
            .values("category")
            .annotate(total=Coalesce(Sum("amount"), Decimal("0.00"), output_field=DecimalField()))
        )
    }
    limits = {
        bc.category: bc.budget_limit
        for bc in BudgetCategory.objects.filter(user=user)
    }
    rows = []
    for cat in set(actuals) | set(limits):
        actual = actuals.get(cat, Decimal("0.00"))
        limit  = limits.get(cat)
        pct    = int((actual / limit) * 100) if limit else None
        rows.append({
            "category": cat,
            "label":    dict(Expense.Category.choices).get(cat, cat.title()),
            "actual":   actual,
            "limit":    limit,
            "pct":      min(pct, 100) if pct is not None else None,
            "over":     actual > limit if limit else False,
        })
    rows.sort(key=lambda x: x["actual"], reverse=True)
    return rows


def get_currency_symbol(profile):
    return "€" if profile.currency == "EUR" else "£"


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@login_required
def profile(request):
    profile = get_object_or_404(UserProfile, user=request.user)

    partner_income = profile.partner_monthly_income or Decimal("0.00")
    monthly_income = profile.monthly_income + partner_income if profile.monthly_income else Decimal("0.00")

    today = timezone.now().date()
    month_start = today.replace(day=1)

    total_expenses = (
        Expense.objects
        .filter(user=request.user, date__gte=month_start, is_upcoming=False)
        .aggregate(total=Coalesce(Sum("amount"), Decimal("0.00"), output_field=DecimalField()))
        .get("total")
    )

    savings_goals = SavingsGoal.objects.filter(user=request.user)
    savings_goals = SavingsGoal.objects.filter(user=request.user)

    total_saved = sum(g.saved_amount for g in savings_goals) or Decimal("0.00")
    total_target = sum(g.target_amount for g in savings_goals) or Decimal("0.00")

    savings_pct = (
        min(100, int((total_saved / total_target) * 100))
        if total_target > 0 else 0
    )
    registry_total = (
        Expense.objects
        .filter(user=request.user, is_upcoming=True)
        .aggregate(total=Coalesce(Sum("amount"), Decimal("0.00"), output_field=DecimalField()))
        .get("total")
    )

    expense_count = Expense.objects.filter(user=request.user, is_upcoming=False).count()
    goals_count = savings_goals.count()

    context = {
        "profile": profile,
        "monthly_income": monthly_income,
        "total_expenses": total_expenses,
        "total_saved": total_saved,
        "registry_total": registry_total,
        "expense_count": expense_count,
        "goals_count": goals_count,
        "pregnancy_week": profile.pregnancy_week,
        "trimester": profile.trimester,
        "weeks_until_due": profile.weeks_until_due,
        "total_saved": total_saved,
        "total_target": total_target,
        "savings_pct": savings_pct,
    }
    return render(request, "profile.html", context)


# ---------------------------------------------------------------------------
# Profile setup
# ---------------------------------------------------------------------------

@login_required
def profile_setup(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = ProfileSetupForm(request.POST, instance=profile)
        if form.is_valid():
            prof = form.save(commit=False)
            prof.user = request.user
            prof.save()
            messages.success(request, "Profile saved.")
            return redirect("dashboard")
    else:
        form = ProfileSetupForm(instance=profile)

    return render(request, "profile_setup.html", {"form": form})


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    from .ml_advisor import get_recommendation

    profile = UserProfile.objects.filter(user=request.user).first()

    if not profile:
        return redirect("profile_setup")
    if profile.monthly_income is None:
        return redirect("profile_setup")
    if profile.life_stage == UserProfile.LifeStage.EXPECTING and not profile.due_date:
        return redirect("profile_setup")
    if profile.life_stage == UserProfile.LifeStage.EARLY and profile.child_age_months is None:
        return redirect("profile_setup")

    today       = timezone.now().date()
    month_start = today.replace(day=1)

    # Income
    partner_income = profile.partner_monthly_income or Decimal("0.00")
    monthly_income = profile.monthly_income + partner_income

    # Actual spend this month
    total_expenses = (
        Expense.objects
        .filter(user=request.user, date__gte=month_start, is_upcoming=False)
        .aggregate(total=Coalesce(Sum("amount"), Decimal("0.00"), output_field=DecimalField()))
        .get("total")
    )

    # Budget goal
    budget_goal = profile.budget_goal or monthly_income
    remaining   = budget_goal - total_expenses

    # Savings goals
    savings_goals = SavingsGoal.objects.filter(user=request.user)
    total_saved = (
        SavingsEntry.objects
        .filter(user=request.user)
        .aggregate(t=Coalesce(Sum("amount"), Decimal("0.00"), output_field=DecimalField()))
        .get("t")
    )

    # Category breakdown (actual spending only — used for budget tracker)
    category_data = _category_budget_data(request.user, month_start)

    # Chart: all expenses by category (actual + upcoming)
    cat_labels = dict(Expense.Category.choices)
    chart_qs = (
        Expense.objects
        .filter(user=request.user)
        .values("category")
        .annotate(total=Coalesce(Sum("amount"), Decimal("0.00"), output_field=DecimalField()))
    )
    chart_categories = sorted(
        [
            {"label": cat_labels.get(row["category"], row["category"].title()),
             "actual": row["total"]}
            for row in chart_qs
            if row["total"] > 0
        ],
        key=lambda x: x["actual"],
        reverse=True,
    )
    chart_data = json.dumps({
        "labels": [c["label"]  for c in chart_categories],
        "values": [float(c["actual"]) for c in chart_categories],
    })

    # Upcoming / milestone / recent expenses
    upcoming_expenses = (
        Expense.objects
        .filter(user=request.user, date__gt=today)
        .order_by("date")[:5]
    )
    milestone_expenses = (
        Expense.objects
        .filter(user=request.user, date__gt=today, is_upcoming=True)
        .exclude(milestone="")
        .order_by("date")[:6]
    )
    recent_expenses = (
        Expense.objects
        .filter(user=request.user, is_upcoming=False)
        .order_by("-date")[:4]
    )

    registry_total = (
        Expense.objects
        .filter(user=request.user, is_upcoming=True)
        .aggregate(total=Coalesce(Sum("amount"), Decimal("0.00"), output_field=DecimalField()))
        .get("total")
    )

    # Pregnancy week / trimester bar
    pregnancy_week     = profile.pregnancy_week
    trimester          = profile.trimester
    weeks_until_due    = profile.weeks_until_due
    trimester_segments = []
    if pregnancy_week is not None:
        for i in range(1, 14):
            week_mid = i * 3
            if week_mid < pregnancy_week:
                state = "done"
            elif week_mid <= pregnancy_week + 3:
                state = "active"
            else:
                state = "future"
            trimester_segments.append({"week": week_mid, "state": state})

    # Weekly tip
    weekly_tip = (
        WeeklyTip.objects
        .filter(week_start__lte=pregnancy_week, week_end__gte=pregnancy_week)
        .first()
    ) if pregnancy_week else None

    # ML recommendation
    ml = None
    if profile.monthly_income:
        if profile.due_date:
            days_left = (profile.due_date - today).days
            months_remaining = max(days_left // 30, 1)
        else:
            months_remaining = 8
        ml = get_recommendation(float(monthly_income), months_remaining)

    context = {
        "profile": profile,
        # income & budget
        "monthly_income":  monthly_income,
        "budget_goal":     budget_goal,
        "total_expenses":  total_expenses,
        "remaining":       remaining,
        # savings
        "savings_goals":   savings_goals,
        "total_saved":     total_saved,
        # categories
        "category_data":   category_data,
        "chart_categories": chart_categories,
        "chart_data":      chart_data,
        # expenses
        "upcoming_expenses":   upcoming_expenses,
        "milestone_expenses":  milestone_expenses,
        "recent_expenses":     recent_expenses,
        "registry_total":      registry_total,
        # pregnancy
        "pregnancy_week":      pregnancy_week,
        "trimester":           trimester,
        "weeks_until_due":     weeks_until_due,
        "trimester_segments":  trimester_segments,
        # tip
        "weekly_tip": weekly_tip,
        # ML
        "ml": ml,
    }
    return render(request, "dashboard.html", context)


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------

@login_required
def timeline(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    today = date.today()

    if profile.due_date:
        days_until_due   = (profile.due_date - today).days
        current_week     = 40 - (days_until_due // 7)
        progress_percent = round((current_week / 40) * 100, 1)
        current_month    = min(max(current_week // 4, 1), 9)
        remaining_weeks  = 40 - current_week
        if current_week <= 13:
            current_trimester = 1
        elif current_week <= 26:
            current_trimester = 2
        else:
            current_trimester = 3
    else:
        current_week      = 0
        progress_percent  = 0
        current_month     = 1
        remaining_weeks   = 40
        current_trimester = 1

    timeline_data = [
        {
            "month": 1,
            "icon": "images/month_icons/discovery.png",
            "icon_type": "horizontal",
            "tasks": ["Take pregnancy test", "Book GP appointment", "Start taking folic acid"],
            "appointments": ["GP confirmation appointment", "Register with midwife"],
            "budget_tips": ["Check maternity pay entitlement", "Start a dedicated baby savings fund"],
        },
        {
            "month": 2,
            "icon": "images/month_icons/doctor.png",
            "icon_type": "horizontal",
            "tasks": ["First prenatal visit", "Start prenatal vitamins", "Avoid alcohol and smoking"],
            "appointments": ["First midwife booking appointment", "Blood tests & health screening"],
            "budget_tips": ["Review your monthly budget", "Look into free prescriptions (MATB1 form)"],
        },
        {
            "month": 3,
            "icon": "images/month_icons/ultrasound.png",
            "icon_type": "horizontal",
            "tasks": ["First ultrasound scan", "Tell close family", "Research maternity leave options"],
            "appointments": ["12-week dating scan", "Combined screening (Down's syndrome test)"],
            "budget_tips": ["Notify HR about pregnancy", "Calculate statutory maternity pay", "Start shopping sales for baby essentials"],
        },
        {
            "month": 4,
            "icon": "images/month_icons/notebook.png",
            "icon_type": "vertical",
            "tasks": ["Anatomy scan", "Start thinking about baby names", "Research childcare costs"],
            "appointments": ["16-week midwife check-up", "Anomaly scan booking"],
            "budget_tips": ["Research childcare vouchers or tax-free childcare", "Begin pricing nurseries and childminders"],
        },
        {
            "month": 5,
            "icon": "images/month_icons/balloons.png",
            "icon_type": "vertical",
            "tasks": ["20-week anatomy scan", "Start baby registry", "Plan nursery design"],
            "appointments": ["20-week anomaly scan"],
            "budget_tips": ["Create a baby registry to guide gift-givers", "Buy big items (cot, pram) early during sales", "Compare second-hand vs new for big purchases"],
        },
        {
            "month": 6,
            "icon": "images/month_icons/nursery.png",
            "icon_type": "horizontal",
            "tasks": ["Buy baby clothes", "Set up nursery", "Research breastfeeding support"],
            "appointments": ["24-week midwife appointment", "Glucose tolerance test (if advised)"],
            "budget_tips": ["Stock up on newborn essentials in bulk", "Look into Sure Start Maternity Grant (if eligible)"],
        },
        {
            "month": 7,
            "icon": "images/month_icons/hospitalbag.png",
            "icon_type": "vertical",
            "tasks": ["Pack hospital bag", "Start prenatal/antenatal classes", "Write birth preferences"],
            "appointments": ["28-week midwife appointment", "Anti-D injection (if Rh negative)", "Iron & blood pressure check"],
            "budget_tips": ["Finalise maternity leave start date with employer", "Set up standing order to baby savings account", "Budget for hospital bag items"],
        },
        {
            "month": 8,
            "icon": "images/month_icons/carseat.png",
            "icon_type": "vertical",
            "tasks": ["Install car seat", "Finalise hospital plan", "Prepare freezer meals"],
            "appointments": ["32-week midwife appointment", "36-week check (position of baby)"],
            "budget_tips": ["Have emergency fund in place before birth", "Check if partner is entitled to paternity pay", "Review insurance policies — add baby after birth"],
        },
        {
            "month": 9,
            "icon": "images/month_icons/babyborn.png",
            "icon_type": "vertical",
            "tasks": ["Prepare hospital documents", "Rest and prepare mentally", "Confirm birth partner plan"],
            "appointments": ["38-week midwife appointment", "40-week check if no labour yet"],
            "budget_tips": ["Register baby for Child Benefit within 3 months of birth", "Open a Junior ISA or savings account for baby", "Plan your first month's budget as a family"],
        },
    ]

    remaining_months = [m for m in timeline_data if m["month"] >= current_month]

    baby_sizes = {
        1: "womb", 8: "raspberry", 12: "lime", 16: "avocado", 20: "banana",
        24: "corn", 28: "eggplant", 32: "coconut", 36: "papaya", 40: "watermelon",
    }
    baby_size = None
    for week in sorted(baby_sizes):
        if current_week >= week:
            baby_size = baby_sizes[week]

    baby_image = f"images/baby_sizes/{baby_size}.png" if baby_size else ""
    due_date_formatted = profile.due_date.strftime("%d %B %Y") if profile.due_date else "Not set"

    context = {
        "profile":          profile,
        "current_week":     current_week,
        "remaining_weeks":  remaining_weeks,
        "progress_percent": progress_percent,
        "current_month":    current_month,
        "timeline":         timeline_data, 
        "baby_size":        baby_size,
        "baby_image":       baby_image,
        "current_trimester": current_trimester,
        "due_date":         due_date_formatted,
    }
    return render(request, "timeline.html", context)


# ---------------------------------------------------------------------------
# Tracker
# ---------------------------------------------------------------------------

@login_required
def tracker(request):
    profile = UserProfile.objects.filter(user=request.user).first()
    if not profile:
        return redirect("profile_setup")

    today = date.today()
    monthly_income = profile.monthly_income or Decimal("0.00")
    partner_income = profile.partner_monthly_income or Decimal("0.00")

    # ---- Countdown ----
    days_until_leave = None
    weeks_until_leave = None
    countdown_dash = 0

    if profile.maternity_leave_start:
        days_until_leave = (profile.maternity_leave_start - today).days
        weeks_until_leave = max(0, days_until_leave // 7)
        ref = 280
        elapsed = max(0, ref - days_until_leave)
        countdown_dash = round(min(elapsed / ref, 1) * 314)

    # ---- Leave duration ----
    leave_weeks_total = 0
    phase_full_weeks = phase_half_weeks = phase_stat_weeks = phase_unpaid_weeks = 0
    phase_full_pct = phase_half_pct = phase_stat_pct = phase_unpaid_pct = 0
    phase_full_monthly = phase_half_monthly = phase_stat_monthly = Decimal("0.00")
    phase_full_start = phase_full_end = None
    phase_half_start = phase_half_end = None
    phase_stat_start = phase_stat_end = None
    phase_unpaid_start = phase_unpaid_end = None
    total_leave_cost = income_drop = avg_monthly_during_leave = Decimal("0.00")
    paid_weeks = 0
    monthly_income_chart = []

    STAT_WEEKLY = Decimal("289.00")
    STAT_MONTHLY = (STAT_WEEKLY * Decimal("52") / Decimal("12")).quantize(Decimal("0.01"))

    if profile.maternity_leave_start and profile.maternity_leave_end:
        delta = (profile.maternity_leave_end - profile.maternity_leave_start).days
        leave_weeks_total = delta // 7

        emp_full = profile.employer_full_pay_weeks if profile.employer_full_pay_weeks is not None else 6
        emp_half = profile.employer_half_pay_weeks if profile.employer_half_pay_weeks is not None else 6

        employer_paid = emp_full + emp_half
        stat_weeks_available = max(0, 26 - employer_paid)

        phase_full_weeks   = min(emp_full, leave_weeks_total)
        phase_half_weeks   = min(emp_half, max(0, leave_weeks_total - phase_full_weeks))
        phase_stat_weeks   = min(stat_weeks_available, max(0, leave_weeks_total - phase_full_weeks - phase_half_weeks))
        phase_unpaid_weeks = max(0, leave_weeks_total - phase_full_weeks - phase_half_weeks - phase_stat_weeks)
        paid_weeks = phase_full_weeks + phase_half_weeks + phase_stat_weeks

        phase_full_monthly = monthly_income
        phase_half_monthly = (monthly_income / 2).quantize(Decimal("0.01"))
        phase_stat_monthly = STAT_MONTHLY

        start = profile.maternity_leave_start
        phase_full_start   = start
        phase_full_end     = start + timedelta(weeks=phase_full_weeks)
        phase_half_start   = phase_full_end
        phase_half_end     = phase_half_start + timedelta(weeks=phase_half_weeks)
        phase_stat_start   = phase_half_end
        phase_stat_end     = phase_stat_start + timedelta(weeks=phase_stat_weeks)
        phase_unpaid_start = phase_stat_end
        phase_unpaid_end   = profile.maternity_leave_end

        max_w = max(phase_full_weeks, phase_half_weeks, phase_stat_weeks, phase_unpaid_weeks, 1)
        phase_full_pct   = round(phase_full_weeks   / max_w * 100)
        phase_half_pct   = round(phase_half_weeks   / max_w * 100)
        phase_stat_pct   = round(phase_stat_weeks   / max_w * 100)
        phase_unpaid_pct = round(phase_unpaid_weeks / max_w * 100)

        weeks_per_month = Decimal("4.33")
        normal_total = monthly_income * Decimal(str(leave_weeks_total)) / weeks_per_month
        actual_total = (
            phase_full_monthly * Decimal(str(phase_full_weeks))  / weeks_per_month +
            phase_half_monthly * Decimal(str(phase_half_weeks))  / weeks_per_month +
            phase_stat_monthly * Decimal(str(phase_stat_weeks))  / weeks_per_month
        )
        total_leave_cost = (normal_total - actual_total).quantize(Decimal("0.01"))
        income_drop = (monthly_income - phase_half_monthly).quantize(Decimal("0.01"))

        months_on_leave = Decimal(str(leave_weeks_total)) / weeks_per_month
        avg_monthly_during_leave = (actual_total / months_on_leave).quantize(Decimal("0.01")) if months_on_leave > 0 else Decimal("0.00")

        cursor = start
        max_amount = float(monthly_income) if monthly_income > 0 else 1
        month_num = 1
        while cursor < profile.maternity_leave_end:
            weeks_elapsed = (cursor - start).days // 7
            if weeks_elapsed < phase_full_weeks:
                phase = "full"
                amount = phase_full_monthly
            elif weeks_elapsed < phase_full_weeks + phase_half_weeks:
                phase = "half"
                amount = phase_half_monthly
            elif weeks_elapsed < phase_full_weeks + phase_half_weeks + phase_stat_weeks:
                phase = "statutory"
                amount = phase_stat_monthly
            else:
                phase = "unpaid"
                amount = Decimal("0.00")

            pct = round(float(amount) / max_amount * 100)
            monthly_income_chart.append({
                "label": f"M{month_num}",
                "amount": amount,
                "phase": phase,
                "pct": pct,
            })
            cursor = cursor + timedelta(weeks=4)
            month_num += 1

    partner_paternity_pay = (STAT_WEEKLY * 2).quantize(Decimal("0.01"))
    partner_normal_monthly = partner_income

    context = {
        "profile": profile,
        "days_until_leave": days_until_leave,
        "weeks_until_leave": weeks_until_leave,
        "countdown_dash": countdown_dash,
        "leave_weeks_total": leave_weeks_total,
        "paid_weeks": paid_weeks,
        "monthly_income": monthly_income,
        "total_leave_cost": total_leave_cost,
        "income_drop": income_drop,
        "avg_monthly_during_leave": avg_monthly_during_leave,
        "phase_full_weeks": phase_full_weeks,
        "phase_half_weeks": phase_half_weeks,
        "phase_stat_weeks": phase_stat_weeks,
        "phase_unpaid_weeks": phase_unpaid_weeks,
        "phase_full_pct": phase_full_pct,
        "phase_half_pct": phase_half_pct,
        "phase_stat_pct": phase_stat_pct,
        "phase_unpaid_pct": phase_unpaid_pct,
        "phase_full_monthly": phase_full_monthly,
        "phase_half_monthly": phase_half_monthly,
        "phase_stat_monthly": phase_stat_monthly,
        "phase_full_start": phase_full_start,
        "phase_full_end": phase_full_end,
        "phase_half_start": phase_half_start,
        "phase_half_end": phase_half_end,
        "phase_stat_start": phase_stat_start,
        "phase_stat_end": phase_stat_end,
        "phase_unpaid_start": phase_unpaid_start,
        "phase_unpaid_end": phase_unpaid_end,
        "monthly_income_chart": monthly_income_chart,
        "partner_paternity_pay": partner_paternity_pay,
        "partner_normal_monthly": partner_normal_monthly,
    }
    return render(request, "tracker.html", context)


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------

@login_required
def goals(request):
    profile = UserProfile.objects.filter(user=request.user).first()
    if not profile:
        return redirect("profile_setup")

    if not Goal.objects.filter(user=request.user).exists():
        seed_goals(request.user)

    goals_qs = Goal.objects.filter(user=request.user)
    goals_total    = goals_qs.count()
    goals_complete = goals_qs.filter(completed=True).count()
    goals_pct      = round(goals_complete / goals_total * 100) if goals_total > 0 else 0
    goals_dash      = round(goals_pct / 100 * 314)
    goals_dash_hero = round(goals_pct / 100 * 415)

    # Savings — pull from SavingsGoal objects
    savings_goals = SavingsGoal.objects.filter(user=request.user)
    total_target  = sum(g.target_amount for g in savings_goals) or Decimal("0.00")
    total_saved   = sum(g.saved_amount  for g in savings_goals) or Decimal("0.00")
    savings_remaining = max(Decimal("0.00"), total_target - total_saved)
    savings_pct   = min(100, round(float(total_saved) / float(total_target) * 100)) if total_target > 0 else 0

    # Recent logs across all savings entries
    savings_logs = SavingsEntry.objects.filter(user=request.user).order_by("-date")[:10]

    goals_list = []
    for g in goals_qs:
        goals_list.append({
            "id":           g.id,
            "title":        g.title,
            "description":  g.description,
            "completed":    g.completed,
            "icon":         g.icon,
            "colour":       g.colour,
            "image":        g.image if hasattr(g, "image") and g.image else None,
        })

    return render(request, "goals.html", {
        "profile":          profile,
        "goals":            goals_list,
        "goals_total":      goals_total,
        "goals_complete":   goals_complete,
        "goals_pct":        goals_pct,
        "goals_dash":       goals_dash,
        "goals_dash_hero":  goals_dash_hero,
        "savings_goals":    savings_goals,
        "savings_logs":     savings_logs,
        "total_saved":      total_saved,
        "total_target":     total_target,
        "savings_remaining": savings_remaining,
        "savings_pct":      savings_pct,
    })

import random

GOAL_MESSAGES = [
    "You're on your way!♥︎ ",
    "One step closer - keep going! ♥︎",
    "Look at you smashing it! ⏾",
    "Every tick counts - you've got this! ❀",
    "Progress made! Your baby will thank you. ♥︎",
    "That's the spirit! One goal down! ✧",
    "You're building something wonderful! ✿",
    "Small wins add up to big things! ✧",
    "Goal ticked - you're amazing! ✿",
    "Your future self is proud of you. ⏾",
]

SAVINGS_MESSAGES = [
    "Savings logged — you're doing brilliantly! ♥︎",
    "Every euro counts — great work! ✿",
    "Look at those savings grow! ✧",
    "That's the one! Keep it up! ♥︎",
    "Your baby bump budget is looking good! ✧",
    "Another step closer to your goal! ✿",
    "Saving superstar! ♥︎",
    "Future you is going to be so grateful! ⏾",
    "Money in the pot — you've got this! ✧",
    "Small deposits, big dreams. Keep going! ⏾",
]
@login_required
def toggle_goal(request, goal_id):
    if request.method == "POST":
        goal = Goal.objects.filter(user=request.user, id=goal_id).first()
        if goal:
            goal.completed = not goal.completed
            goal.save()
            if goal.completed:
                messages.success(request, random.choice(GOAL_MESSAGES))
    return redirect("goals")

@login_required
def add_savings(request):
    if request.method == "POST":
        amount_str = request.POST.get("amount", "").strip()
        date_str   = request.POST.get("date", "").strip()
        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                raise ValueError
            if not date_str:
                raise ValueError
            SavingsEntry.objects.create(
                user=request.user,
                amount=amount,
                note=request.POST.get("note", ""),
                date=date_str,
            )
            messages.success(request, "Savings logged.")
        except (ValueError, Exception):
            messages.error(request, "Please enter a valid amount and date.")
    return redirect(request.META.get("HTTP_REFERER", "goals"))


def seed_goals(user):
    defaults = [
        {"title": "Build an emergency fund",   "description": "Set aside savings to cover unexpected costs.",          "icon": "🛡",  "colour": "green", "image": "images/goals/emergency.png",  "target_amount": None},
        {"title": "Plan for maternity leave",  "description": "Prepare for reduced income during time off.",           "icon": "📅",  "colour": "sage",  "image": "images/goals/maternity.png",  "target_amount": None},
        {"title": "Save for baby essentials",  "description": "Budget for furniture, clothing, and equipment.",        "icon": "🧸",  "colour": "amber", "image": "images/goals/essentials.png", "target_amount": None},
        {"title": "Prepare for childcare",     "description": "Estimate childcare costs and available supports.",      "icon": "🏫",  "colour": "green", "image": "images/goals/childcare.png",  "target_amount": None},
        {"title": "Long-term savings plan",    "description": "Build ongoing savings for your family's future.",       "icon": "📈",  "colour": "sage",  "image": "images/goals/savings.png",    "target_amount": None},
        {"title": "Review your insurance",     "description": "Make sure your cover grows with your family.",          "icon": "📋",  "colour": "amber", "image": "images/goals/insurance.png",  "target_amount": None},
    ]
    for g in defaults:
        Goal.objects.create(user=user, **g)


# ---------------------------------------------------------------------------
# Expenses
# ---------------------------------------------------------------------------

@login_required
def add_expense(request):
    if request.method == "POST":
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            messages.success(request, "Expense added.")
            return redirect("dashboard")
    else:
        form = ExpenseForm()
    return render(request, "add_expense.html", {"form": form})


@login_required
def edit_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == "POST":
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, "Expense updated.")
            return redirect("expense_list")
    else:
        form = ExpenseForm(instance=expense)
    return render(request, "add_expense.html", {"form": form, "editing": True})


@login_required
def delete_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == "POST":
        expense.delete()
        messages.success(request, "Expense deleted.")
    return redirect("expense_list")


@login_required
def expense_list(request):
    expenses = Expense.objects.filter(user=request.user).order_by("-date")
    return render(request, "expense_list.html", {"expenses": expenses})


# ---------------------------------------------------------------------------
# Savings goals (CRUD)
# ---------------------------------------------------------------------------

@login_required
def savings_goals(request):
    profile = request.user.userprofile
    savings_goals = SavingsGoal.objects.filter(user=request.user)
    savings_logs = SavingsEntry.objects.filter(user=request.user)[:5]

    # Roll up totals across all goals
    total_target = sum(g.target_amount for g in savings_goals) or Decimal("0.00")
    total_saved = sum(g.saved_amount for g in savings_goals) or Decimal("0.00")
    savings_remaining = max(Decimal("0.00"), total_target - total_saved)
    savings_pct = min(100, int((total_saved / total_target) * 100)) if total_target else 0

    return render(request, "savings_goals.html", {
        "savings_goals": savings_goals,
        "savings_logs": savings_logs,
        "total_saved": total_saved,
        "total_target": total_target,
        "savings_remaining": savings_remaining,
        "savings_pct": savings_pct,
    })
@login_required
def add_savings_goal(request):
    if request.method == "POST":
        name          = request.POST.get("name", "").strip()
        target_amount = request.POST.get("target_amount", "0").strip()
        color         = request.POST.get("color", "green").strip()
        if name and target_amount:
            try:
                SavingsGoal.objects.create(
                    user=request.user,
                    name=name,
                    target_amount=Decimal(target_amount),
                    color=color,
                )
                messages.success(request, "Goal added!")
            except Exception:
                messages.error(request, "Invalid amount.")
    return redirect("goals")


@login_required
def edit_savings_goal(request, pk):
    goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)
    if request.method == "POST":
        name          = request.POST.get("name", "").strip()
        target_amount = request.POST.get("target_amount", "0").strip()
        saved_amount  = request.POST.get("saved_amount", "0").strip()
        if name and target_amount:
            try:
                goal.name          = name
                goal.target_amount = Decimal(target_amount)
                goal.saved_amount  = Decimal(saved_amount)
                goal.save()
                messages.success(request, "Goal updated!")
            except Exception:
                messages.error(request, "Invalid amount.")
    return redirect("goals")

@login_required
def delete_savings_goal(request, pk):
    goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)
    if request.method == "POST":
        goal.delete()
        messages.success(request, "Goal deleted.")
    return redirect("goals")


@login_required
def log_to_goal(request, pk):
    goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)
    if request.method == "POST":
        amount = request.POST.get("amount", "").strip()
        note   = request.POST.get("note", "").strip()
        try:
            amount = Decimal(amount)
            if amount > 0:
                SavingsEntry.objects.create(
                    user=request.user,
                    amount=amount,
                    note=note,
                    date=timezone.now().date(),
                )
                goal.saved_amount += amount
                goal.save()
                messages.success(request, random.choice(SAVINGS_MESSAGES))
        except Exception:
            messages.error(request, "Invalid amount.")
    return redirect("goals")

# ---------------------------------------------------------------------------
# Budget category limits
# ---------------------------------------------------------------------------

@login_required
def budget_setup(request):
    existing = {bc.category: bc for bc in BudgetCategory.objects.filter(user=request.user)}

    if request.method == "POST":
        for cat_value, _ in Expense.Category.choices:
            limit_str = request.POST.get(f"limit_{cat_value}", "").strip()
            if limit_str:
                try:
                    bc, _ = BudgetCategory.objects.get_or_create(user=request.user, category=cat_value)
                    bc.budget_limit = Decimal(limit_str)
                    bc.save()
                except Exception:
                    pass
            elif cat_value in existing:
                existing[cat_value].delete()

        messages.success(request, "Budget limits saved.")
        return redirect("dashboard")

    categories = [
        {"value": v, "label": l, "limit": existing[v].budget_limit if v in existing else ""}
        for v, l in Expense.Category.choices
    ]
    return render(request, "budget_setup.html", {"categories": categories})


# ---------------------------------------------------------------------------
# Community
# ---------------------------------------------------------------------------

@login_required
def community(request):
    category = request.GET.get("category", "")

    posts = Post.objects.filter(is_removed=False).annotate(
        num_likes=Count("likes", distinct=True),
        num_replies=Count("replies", distinct=True),
    ).order_by("-is_pinned", "-created_at")

    if category:
        posts = posts.filter(category=category)

    liked_ids = set(
        Like.objects.filter(user=request.user).values_list("post_id", flat=True)
    )

    recent_conversations = []
    for convo in request.user.conversations.order_by('-updated_at')[:3]:
        other = convo.other_participant(request.user)
        last_msg = convo.last_message()
        recent_conversations.append({
            'id': convo.id,
            'other': other,
            'last': last_msg,
        })

    context = {
        "posts": posts,
        "liked_ids": liked_ids,
        "categories": Post.Category.choices,
        "active_category": category,
        "post_form": PostForm(),
        "recent_conversations": recent_conversations,
    }
    return render(request, "community.html", context)


@login_required
def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk, is_removed=False)
    replies = post.replies.filter(is_removed=False)
    user_liked = Like.objects.filter(post=post, user=request.user).exists()

    if request.method == "POST":
        form = ReplyForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.post = post
            reply.author = request.user
            reply.save()
            messages.success(request, "Reply posted.")
            return redirect("post_detail", pk=pk)
    else:
        form = ReplyForm()
    recent_conversations = request.user.conversations.order_by('-updated_at')[:3]
    context = {
        "post": post,
        "replies": replies,
        "reply_form": form,
        "user_liked": user_liked,
        "recent_conversations": recent_conversations,
    }
    return render(request, "post_detail.html", context)


@login_required
def create_post(request):
    if request.method == "POST":
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, "Post created.")
            return redirect("post_detail", pk=post.pk)
    else:
        form = PostForm()
    return render(request, "post_form.html", {"form": form})


@login_required
def edit_post(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user, is_removed=False)

    if request.method == "POST":
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, "Post updated.")
            return redirect("post_detail", pk=pk)
    else:
        form = PostForm(instance=post)

    return render(request, "post_form.html", {"form": form, "editing": True, "post": post})


@login_required
def delete_post(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user)
    if request.method == "POST":
        post.delete()
        messages.success(request, "Post deleted.")
        return redirect("community")
    return redirect("post_detail", pk=pk)


@login_required
def edit_reply(request, pk):
    reply = get_object_or_404(Reply, pk=pk, author=request.user, is_removed=False)

    if request.method == "POST":
        form = ReplyForm(request.POST, instance=reply)
        if form.is_valid():
            form.save()
            messages.success(request, "Reply updated.")
    return redirect("post_detail", pk=reply.post.pk)


@login_required
def delete_reply(request, pk):
    reply = get_object_or_404(Reply, pk=pk, author=request.user)
    post_pk = reply.post.pk
    if request.method == "POST":
        reply.delete()
        messages.success(request, "Reply deleted.")
    return redirect("post_detail", pk=post_pk)


@login_required
def toggle_like(request, pk):
    post = get_object_or_404(Post, pk=pk, is_removed=False)
    like, created = Like.objects.get_or_create(post=post, user=request.user)

    if not created:
        like.delete()
        liked = False
    else:
        liked = True

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"liked": liked, "count": post.like_count})

    return redirect(request.META.get("HTTP_REFERER", "community"))


@login_required
def pin_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.user.is_staff and request.method == "POST":
        post.is_pinned = not post.is_pinned
        post.save()
    return redirect("post_detail", pk=pk)


@login_required
def remove_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.user.is_staff and request.method == "POST":
        post.is_removed = True
        post.save()
        messages.success(request, "Post removed.")
        return redirect("community")
    return redirect("post_detail", pk=pk)


@login_required
def remove_reply(request, pk):
    reply = get_object_or_404(Reply, pk=pk)
    if request.user.is_staff and request.method == "POST":
        reply.is_removed = True
        reply.save()
        messages.success(request, "Reply removed.")
    return redirect("post_detail", pk=reply.post.pk)


# ---------------------------------------------------------------------------
# Staff dashboard
# ---------------------------------------------------------------------------

@login_required
def staff_dashboard(request):
    if not request.user.is_staff:
        return redirect("dashboard")

    from django.contrib.auth.models import User as AuthUser
    users = AuthUser.objects.select_related("userprofile").order_by("date_joined")
    posts = Post.objects.select_related("author").order_by("-created_at")
    total_users   = users.count()
    total_posts   = posts.count()
    removed_posts = posts.filter(is_removed=True).count()
    pinned_posts  = posts.filter(is_pinned=True, is_removed=False).count()

    return render(request, "staff_dashboard.html", {
        "users":         users,
        "posts":         posts,
        "total_users":   total_users,
        "total_posts":   total_posts,
        "removed_posts": removed_posts,
        "pinned_posts":  pinned_posts,
    })


@login_required
def staff_toggle_role(request, user_id):
    if not request.user.is_staff or request.method != "POST":
        return redirect("staff_dashboard")
    from django.contrib.auth.models import User as AuthUser
    target = get_object_or_404(AuthUser, pk=user_id)
    if target == request.user:
        messages.error(request, "You cannot change your own role.")
        return redirect("staff_dashboard")
    target.is_staff = not target.is_staff
    target.save()
    role = "Staff" if target.is_staff else "User"
    messages.success(request, f"{target.username} is now {role}.")
    return redirect("staff_dashboard")


@login_required
def staff_delete_user(request, user_id):
    if not request.user.is_staff or request.method != "POST":
        return redirect("staff_dashboard")
    from django.contrib.auth.models import User as AuthUser
    target = get_object_or_404(AuthUser, pk=user_id)
    if target == request.user:
        messages.error(request, "You cannot delete your own account here.")
        return redirect("staff_dashboard")
    username = target.username
    target.delete()
    messages.success(request, f"User '{username}' has been deleted.")
    return redirect("staff_dashboard")

# ===========================================================================
# PRIVATE MESSAGING
# ===========================================================================

from .models import Conversation, Message

@login_required
def inbox(request):
    conversations = Conversation.objects.filter(participants=request.user)
    
    conv_data = []
    for conv in conversations:
        other = conv.participants.exclude(id=request.user.id).first()
        last = conv.messages.order_by('-created_at').first()
        conv_data.append({
            'id': conv.id,
            'other': other,
            'last': last,
        })
    
    unread_count = sum(
        1 for c in conv_data 
        if c['last'] and not c['last'].is_read and c['last'].sender != request.user
    )
    
    return render(request, 'inbox.html', {
        'conversations': conv_data,
        'unread_count': unread_count,
        'active_conversation': None,
        'messages_list': [],
        'other_user': None,
    })


@login_required
def conversation_detail(request, conversation_id):
    conversation = get_object_or_404(
        Conversation, id=conversation_id, participants=request.user
    )

    # Mark messages as read
    conversation.messages.exclude(sender=request.user).update(is_read=True)

    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        if body:
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                body=body,
            )
            conversation.save()
            return redirect('conversation_detail', conversation_id=conversation.id)

    messages_list = conversation.messages.all().order_by('created_at')
    other_user = conversation.participants.exclude(id=request.user.id).first()

    return render(request, 'conversation.html', {
        'conversation': conversation,
        'messages_list': messages_list,
        'other_user': other_user,
    })


@login_required
def start_conversation(request, user_id):
    other_user = get_object_or_404(User, id=user_id)

    if other_user == request.user:
        return redirect('inbox')

    existing = Conversation.objects.filter(
        participants=request.user
    ).filter(
        participants=other_user
    ).first()

    if existing:
        return redirect('conversation_detail', conversation_id=existing.id)

    conversation = Conversation.objects.create()
    conversation.participants.add(request.user, other_user)
    return redirect('conversation_detail', conversation_id=conversation.id)