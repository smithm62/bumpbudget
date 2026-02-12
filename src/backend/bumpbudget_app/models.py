from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator


class UserProfile(models.Model):
    class LifeStage(models.TextChoices):
        EXPECTING = "EXPECTING", "Expecting (pregnant)"
        EARLY = "EARLY", "Early parenthood (0–2 years)"
        PLANNING = "PLANNING", "Planning to try"

    class Currency(models.TextChoices):
        EUR = "EUR", "EUR (€)"
        GBP = "GBP", "GBP (£)"

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # High-level stage
    life_stage = models.CharField(
        max_length=20,
        choices=LifeStage.choices,
        default=LifeStage.EXPECTING,
    )

    # Expecting-specific
    due_date = models.DateField(null=True, blank=True)

    # Early-parenthood-specific
    child_age_months = models.IntegerField(
    null=True,
    blank=True,
    validators=[MinValueValidator(0), MaxValueValidator(24)],
)


    # Income / leave
    monthly_income = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    partner_monthly_income = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00"))]
    )

    maternity_leave_start = models.DateField(null=True, blank=True)
    maternity_leave_end = models.DateField(null=True, blank=True)

    # Savings goals
    savings_goal_total = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    savings_deadline = models.DateField(null=True, blank=True)

    # Preferences / planning assumptions (useful for forecasting)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.EUR)

    created_at = models.DateTimeField(auto_now_add=True)

    




    def __str__(self):
        return f"{self.user.username} profile"

