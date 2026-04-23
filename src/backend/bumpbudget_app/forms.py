from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms
from django.utils import timezone
from .models import UserProfile, Expense, SavingsGoal, BudgetCategory
from .models import Post, Reply


# ---------------------------------------------------------------------------
# Auth forms
# ---------------------------------------------------------------------------

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


# ---------------------------------------------------------------------------
# Profile setup form (merged)
# ---------------------------------------------------------------------------

class ProfileSetupForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            "life_stage",
            "due_date",
            #"child_age_months",
            "monthly_income",
            "partner_monthly_income",
            "maternity_leave_start",
            "maternity_leave_end",
            "employer_full_pay_weeks",
            "employer_half_pay_weeks",
            "taking_additional_unpaid",
            "additional_unpaid_weeks",
            "currency",
            "first_name",
        ]
        widgets = {
            "due_date":              forms.DateInput(attrs={"type": "date"}),
            "maternity_leave_start": forms.DateInput(attrs={"type": "date"}),
            "maternity_leave_end":   forms.DateInput(attrs={"type": "date"}),
            "savings_deadline":      forms.DateInput(attrs={"type": "date"}),
            "employer_full_pay_weeks": forms.NumberInput(attrs={
                "placeholder": "e.g. 6", "min": 0, "max": 26
            }),
            "employer_half_pay_weeks": forms.NumberInput(attrs={
                "placeholder": "e.g. 6", "min": 0, "max": 26
            }),
            "additional_unpaid_weeks": forms.NumberInput(attrs={
                "placeholder": "e.g. 8", "min": 0, "max": 16
            }),
        }
        labels = {
            "employer_full_pay_weeks":  "Weeks of full pay from employer",
            "employer_half_pay_weeks":  "Weeks of half pay from employer",
            "taking_additional_unpaid": "Are you taking additional unpaid leave?",
            "additional_unpaid_weeks":  "How many additional unpaid weeks?",
            "first_name":               "Your first name (optional)",
            "budget_goal":              "Monthly baby budget (optional)",
        }
        help_texts = {
            "life_stage":              "Choose the stage that best matches your situation.",
            "due_date":                "If you're expecting, enter your estimated due date.",
            #"child_age_months":        "If you're in early parenthood, enter your child's age in months (0–24).",
            "monthly_income":          "Your average monthly take-home income.",
            "partner_monthly_income":  "Optional: partner's monthly take-home income.",
            "employer_full_pay_weeks": "How many weeks does your employer pay your full salary? Leave blank if unsure.",
            "employer_half_pay_weeks": "How many weeks does your employer pay half your salary? Leave blank if unsure.",
            "taking_additional_unpaid": "In Ireland you can take up to 16 extra unpaid weeks after the 26 paid weeks.",
            "additional_unpaid_weeks": "How many of the optional unpaid weeks are you planning to take? (0–16)",
            "budget_goal":             "Optional: your monthly pregnancy/baby spending target.",
        }

    def clean(self):
        cleaned = super().clean()
        life_stage       = cleaned.get("life_stage")
        due_date         = cleaned.get("due_date")
        #child_age_months = cleaned.get("child_age_months")
        leave_start      = cleaned.get("maternity_leave_start")
        leave_end        = cleaned.get("maternity_leave_end")
        savings_deadline = cleaned.get("savings_deadline")
        emp_full         = cleaned.get("employer_full_pay_weeks")
        emp_half         = cleaned.get("employer_half_pay_weeks")
        taking_unpaid    = cleaned.get("taking_additional_unpaid")
        unpaid_weeks     = cleaned.get("additional_unpaid_weeks")

        today = timezone.now().date()

        # Life stage rules (UPDATED)
        if life_stage == UserProfile.LifeStage.EXPECTING:
            if not due_date:
                self.add_error("due_date", "Due date is required if you are expecting.")
                
        # Leave date rules
        if leave_start and leave_end and leave_start > leave_end:
            self.add_error("maternity_leave_end", "Leave end date must be after the start date.")

        # Employer pay weeks can't exceed 26 combined
        if emp_full is not None and emp_half is not None:
            if emp_full + emp_half > 26:
                self.add_error(
                    "employer_half_pay_weeks",
                    "Full pay and half pay weeks combined cannot exceed 26 weeks.",
                )

        # Unpaid weeks only valid if taking_additional_unpaid is checked
        if not taking_unpaid and unpaid_weeks:
            cleaned["additional_unpaid_weeks"] = None

        if taking_unpaid and (unpaid_weeks is None or unpaid_weeks == 0):
            self.add_error("additional_unpaid_weeks", "Please enter how many unpaid weeks you plan to take.")

        # Savings deadline should be today or later
        if savings_deadline and savings_deadline < today:
            self.add_error("savings_deadline", "Savings deadline should be today or later.")

        return cleaned


# ---------------------------------------------------------------------------
# Expense, savings, and budget forms
# ---------------------------------------------------------------------------

class ExpenseForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = Expense
        fields = ["category", "description", "amount", "date", "is_upcoming", "milestone", "notes"]
        labels = {
            "is_upcoming": "This is a planned future expense (not yet spent)",
            "milestone":   "Link to a pregnancy milestone (optional)",
        }
        help_texts = {
            "is_upcoming": "Planned expenses show as 'upcoming' on your dashboard.",
            "milestone":   "Milestone expenses appear in the pregnancy timeline.",
        }


class SavingsGoalForm(forms.ModelForm):
    class Meta:
        model = SavingsGoal
        fields = ["name", "target_amount", "saved_amount", "color"]
        labels = {
            "target_amount": "Target amount",
            "saved_amount":  "Amount saved so far",
        }


class BudgetCategoryForm(forms.ModelForm):
    class Meta:
        model = BudgetCategory
        fields = ["category", "budget_limit"]
        labels = {
            "budget_limit": "Monthly limit",
        }


# ---------------------------------------------------------------------------
# Community / forum forms
# ---------------------------------------------------------------------------

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["category", "title", "body", "is_anonymous"]
        widgets = {
            "title": forms.TextInput(attrs={
                "placeholder": "What's on your mind?",
            }),
            "body": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": "Share your experience, question, or tip...",
            }),
        }
        labels = {
            "is_anonymous": "Post anonymously (your name won't be shown)",
            "body":         "Post",
        }


class ReplyForm(forms.ModelForm):
    class Meta:
        model = Reply
        fields = ["body", "is_anonymous"]
        widgets = {
            "body": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Write a reply...",
            }),
        }
        labels = {
            "is_anonymous": "Reply anonymously",
            "body":         "Your reply",
        }