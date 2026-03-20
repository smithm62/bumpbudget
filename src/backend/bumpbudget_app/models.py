from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


# ===========================================================================
# USER PROFILE
# ===========================================================================

class UserProfile(models.Model):
    class LifeStage(models.TextChoices):
        EXPECTING = "EXPECTING", "Expecting (pregnant)"
        EARLY     = "EARLY",     "Early parenthood (0–2 years)"
        PLANNING  = "PLANNING",  "Planning to try"

    class Currency(models.TextChoices):
        EUR = "EUR", "EUR (€)"
        GBP = "GBP", "GBP (£)"

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    life_stage = models.CharField(          # fixed typo: CharFiead → CharField
        max_length=20,
        choices=LifeStage.choices,
        default=LifeStage.EXPECTING,
    )

    due_date = models.DateField(null=True, blank=True)

    child_age_months = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(24)],
    )

    monthly_income = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    partner_monthly_income = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    maternity_leave_start = models.DateField(null=True, blank=True)
    maternity_leave_end   = models.DateField(null=True, blank=True)

    # From old file — employer pay / unpaid leave detail
    employer_full_pay_weeks   = models.IntegerField(null=True, blank=True)
    employer_half_pay_weeks   = models.IntegerField(null=True, blank=True)
    taking_additional_unpaid  = models.BooleanField(default=False)
    additional_unpaid_weeks   = models.IntegerField(null=True, blank=True)

    savings_goal_total = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    savings_deadline = models.DateField(null=True, blank=True)

    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.EUR)

    # From new file — personalisation & budget
    first_name  = models.CharField(max_length=50, blank=True)
    budget_goal = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Monthly pregnancy/baby spending target",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # --- Computed properties (no migration needed) ---

    @property
    def pregnancy_week(self):
        """Current pregnancy week (1–40). None if no due_date."""
        if not self.due_date:
            return None
        from django.utils import timezone
        today = timezone.now().date()
        days_until_due = (self.due_date - today).days
        week = 40 - (days_until_due // 7)
        return max(1, min(40, week))

    @property
    def trimester(self):
        week = self.pregnancy_week
        if week is None:
            return None
        if week <= 13:
            return 1
        elif week <= 27:
            return 2
        return 3

    @property
    def weeks_until_due(self):
        if not self.due_date:
            return None
        from django.utils import timezone
        today = timezone.now().date()
        days = (self.due_date - today).days
        return max(0, days // 7)

    @property
    def currency_symbol(self):
        return "£" if self.currency == self.Currency.GBP else "€"

    def __str__(self):
        return f"{self.user.username} profile"


# ===========================================================================
# EXPENSES
# ===========================================================================

class Expense(models.Model):
    # New file has a richer category + milestone set — kept in full
    class Category(models.TextChoices):
        PRENATAL  = "prenatal",  "Prenatal care"
        NURSERY   = "nursery",   "Nursery"
        CLOTHING  = "clothing",  "Clothing & gear"
        HEALTH    = "health",    "Health & vitamins"
        CHILDCARE = "childcare", "Childcare"
        FOOD      = "food",      "Food"
        TRANSPORT = "transport", "Transport"
        INSURANCE = "insurance", "Insurance"
        OTHER     = "other",     "Other"

    class Milestone(models.TextChoices):
        NONE       = "",           "None"
        SCAN       = "scan",       "Scan / appointment"
        BIRTH_PREP = "birth_prep", "Birth preparation"
        SHOWER     = "shower",     "Baby shower"
        NURSERY    = "nursery",    "Nursery setup"
        POSTBIRTH  = "postbirth",  "Post-birth"

    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name="expenses")
    category    = models.CharField(max_length=50, choices=Category.choices)
    description = models.CharField(max_length=200, blank=True)
    amount      = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    date        = models.DateField()
    is_upcoming = models.BooleanField(
        default=False,
        help_text="Planned future expense — not yet spent",
    )
    milestone   = models.CharField(
        max_length=20, choices=Milestone.choices, blank=True, default="",
    )
    notes       = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.user.username} – {self.get_category_display()} {self.amount} on {self.date}"


# ===========================================================================
# SAVINGS
# ===========================================================================

class SavingsEntry(models.Model):
    """Each time the user logs money saved toward their goal (from old file)."""
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="savings_entries")
    amount     = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    note       = models.CharField(max_length=200, blank=True)
    date       = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.user.username} saved €{self.amount} on {self.date}"


class SavingsGoal(models.Model):
    """Named savings pot with a target and progress tracking (from new file)."""
    COLOR_CHOICES = [
        ("purple", "Purple"),
        ("teal",   "Teal"),
        ("coral",  "Coral"),
        ("blue",   "Blue"),
        ("green",  "Green"),
        ("amber",  "Amber"),
    ]

    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name="savings_goals")
    name          = models.CharField(max_length=100)
    target_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    saved_amount  = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    color         = models.CharField(max_length=20, choices=COLOR_CHOICES, default="purple")
    order         = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    @property
    def progress_pct(self):
        if not self.target_amount:
            return 0
        return min(100, int((self.saved_amount / self.target_amount) * 100))

    @property
    def remaining(self):
        return max(Decimal("0.00"), self.target_amount - self.saved_amount)

    def __str__(self):
        return f"{self.user.username} – {self.name}"


# ===========================================================================
# BUDGET
# ===========================================================================

class BudgetCategory(models.Model):
    """Optional monthly spend limit per Expense.Category."""
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name="budget_categories")
    category     = models.CharField(max_length=50, choices=Expense.Category.choices)
    budget_limit = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        unique_together = ("user", "category")

    def __str__(self):
        return f"{self.user.username} – {self.category}: {self.budget_limit}"


# ===========================================================================
# BABY SHOPPING CHECKLIST  (from old file)
# ===========================================================================

class BabyChecklistItem(models.Model):
    class Category(models.TextChoices):
        NURSERY  = "NURSERY",  "Nursery & Sleep"
        FEEDING  = "FEEDING",  "Feeding"
        CLOTHING = "CLOTHING", "Clothing"
        TRAVEL   = "TRAVEL",   "Pram & Travel"
        BATHING  = "BATHING",  "Bathing & Changing"
        HEALTH   = "HEALTH",   "Health & Safety"
        OTHER    = "OTHER",    "Other"

    user            = models.ForeignKey(User, on_delete=models.CASCADE, related_name="checklist_items")
    category        = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    name            = models.CharField(max_length=200)
    estimated_cost  = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    purchased       = models.BooleanField(default=False)
    purchased_on    = models.DateField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        status = "✓" if self.purchased else "○"
        return f"{status} {self.user.username} — {self.name} ({self.category})"


# ===========================================================================
# GOALS  (from old file)
# ===========================================================================

class Goal(models.Model):
    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name="goals")
    title         = models.CharField(max_length=200)
    description   = models.TextField(blank=True)
    icon          = models.CharField(max_length=10, default="🎯")
    colour        = models.CharField(max_length=20, default="green")
    image         = models.CharField(max_length=200, blank=True, default="")
    completed     = models.BooleanField(default=False)
    target_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user.username} — {self.title}"


# ===========================================================================
# WEEKLY TIPS  (from new file)
# ===========================================================================

class WeeklyTip(models.Model):
    """A financial tip shown on the dashboard for a range of pregnancy weeks."""
    week_start = models.PositiveIntegerField()
    week_end   = models.PositiveIntegerField()
    tip_label  = models.CharField(max_length=80, blank=True)
    tip_text   = models.TextField()

    class Meta:
        ordering = ["week_start"]

    def __str__(self):
        return f"Wk {self.week_start}–{self.week_end}: {self.tip_label}"


# ===========================================================================
# COMMUNITY — Posts, Replies, Likes  (from new file)
# ===========================================================================

class Post(models.Model):
    class Category(models.TextChoices):
        GENERAL      = "general",   "General"
        COSTS        = "costs",     "Costs & budgeting"
        WEEK_BY_WEEK = "week",      "Week by week"
        MATERNITY    = "maternity", "Maternity leave"
        NURSERY      = "nursery",   "Nursery & gear"
        WELLBEING    = "wellbeing", "Wellbeing"

    author       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    category     = models.CharField(max_length=20, choices=Category.choices, default=Category.GENERAL)
    title        = models.CharField(max_length=200)
    body         = models.TextField()
    is_anonymous = models.BooleanField(default=False, help_text="Hide your name on this post")
    is_pinned    = models.BooleanField(default=False)
    is_removed   = models.BooleanField(default=False, help_text="Hidden by staff")
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_pinned", "-created_at"]

    @property
    def display_name(self):
        if self.is_anonymous:
            return "Anonymous"
        try:
            return self.author.userprofile.first_name or self.author.username
        except Exception:
            return self.author.username

    @property
    def like_count(self):
        return self.likes.count()

    @property
    def reply_count(self):
        return self.replies.filter(is_removed=False).count()

    def __str__(self):
        return self.title


class Reply(models.Model):
    post         = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="replies")
    author       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="replies")
    body         = models.TextField()
    is_anonymous = models.BooleanField(default=False)
    is_removed   = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    @property
    def display_name(self):
        if self.is_anonymous:
            return "Anonymous"
        try:
            return self.author.userprofile.first_name or self.author.username
        except Exception:
            return self.author.username

    def __str__(self):
        return f"Reply by {self.author.username} on {self.post.title}"


class Like(models.Model):
    post       = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "user")

    def __str__(self):
        return f"{self.user.username} likes {self.post.title}"