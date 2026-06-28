from django.db import models
from django.contrib.auth.models import User


class Transaction(models.Model):
    user             = models.ForeignKey(User, on_delete=models.CASCADE)
    date             = models.DateField()
    time             = models.TimeField()
    transaction_type = models.CharField(max_length=10)
    amount           = models.DecimalField(max_digits=10, decimal_places=2)
    detail           = models.CharField(max_length=200)

    class Meta:
        ordering = ['-date', '-time']

    def __str__(self):
        return f"{self.transaction_type} ₹{self.amount} - {self.detail}"
