from django.db import models, transaction
from django.utils import timezone
from django.db.models import Max, Sum
from rest_framework.exceptions import ValidationError

from menu.models import Product, MenuVariant


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'  # Paid and being prepared
        COMPLETED = 'completed', 'Completed'  # Order finished

    class DeliveryMode(models.TextChoices):
        TAKE_AWAY = 'take_away', 'Take Away'
        EAT_IN = 'eat_in', 'Eat In'

    order_number = models.PositiveIntegerField() # Daily order number (resets each day)
    order_date = models.DateField(auto_now_add=True) # Date of the order (used for daily numbering)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text="Current status of the order"
    )
    service_type = models.CharField(
        max_length=20,
        choices=DeliveryMode.choices,
        null=True,
        blank=True,
        help_text="Order service type: Take Away or Eat In"
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    class Meta:
        db_table = 'order'
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        unique_together = ('order_number', 'order_date')

    def save(self, *args, **kwargs):
        """
        Override save to auto-generate daily order number and
        prevent marking as completed/processing if not fully paid.
        """
        if self.status in (self.Status.COMPLETED, self.Status.PROCESSING)  and not self.is_fully_paid:
            raise ValidationError("Cannot mark order as processing or completed before full payment.")
        if not self.pk:
            today = timezone.localdate()
            last_number = Order.objects.filter(order_date=today).aggregate(
                max_number=Max('order_number')
            )['max_number'] or 0
            self.order_date = today
            self.order_number = last_number + 1
        super().save(*args, **kwargs)

    def update_total_price(self):
        """
        Recalculate and update the total price from related order items.
        """
        total_price_agg = self.order_items.aggregate(
            total_price=Sum('total_price')
        )['total_price'] or 0
        if self.total_price != total_price_agg:
            self.total_price = total_price_agg
            self.save(update_fields=['total_price'])

    def update_status(self):
        """
        Update order status from PENDING to PROCESSING if fully paid.
        """
        if self.status == self.Status.PENDING and self.is_fully_paid:
            self.status = self.Status.PROCESSING
            self.save(update_fields=['status'])

    @property
    def is_fully_paid(self):
        """
        Check if total payments cover the order total price.
        """
        total_paid = self.payments.aggregate(total=Sum('amount'))['total'] or 0
        return total_paid == (self.total_price or 0)



class OrderItem(models.Model):
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='order_items'
    )
    product = models.ForeignKey(
        Product,
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )
    menu_variant = models.ForeignKey(
        MenuVariant,
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )

    class Meta:
        db_table = 'order_item'
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def clean(self):
        """
        Validate that either product or menu variant is set (but not both).
        """
        if not self.product and not self.menu_variant:
            raise ValidationError("Either a product or a menu variant must be specified.")
        if self.product and self.menu_variant:
            raise ValidationError("You can't set both a product and a menu variant.")

    def save(self, *args, **kwargs):
        self.full_clean()
        self.total_price = self.unit_price * self.quantity
        with transaction.atomic():
            super().save(*args, **kwargs)
            self.order.update_total_price()


class Payment(models.Model):
    class PaymentMode(models.TextChoices):
        CARD = 'card', 'Payment by card'
        CASH = 'cash', 'Payment by cash'
        MOBILE_MONEY = 'mobile money', 'Payment by mobile money'

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    mode = models.CharField(
        max_length=20,
        choices=PaymentMode.choices,
        default=PaymentMode.CASH,
        help_text="Payment mode: Card, Cash or mobile money"
    )

    class Meta:
        db_table = 'payment'
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    def clean(self):
        """
        Prevent total payments from exceeding the order total.
        """
        total_paid = self.order.payments.aggregate(total=Sum('amount'))['total'] or 0
        if total_paid + self.amount > self.order.total_price:
            excess = total_paid + self.amount - self.order.total_price
            raise ValidationError(f"Total payment exceeds the order total by {excess:.2f}.")

    def save(self, *args, **kwargs):
        """
       Validate and save payment, then update order status atomically.
       """
        self.full_clean()
        with transaction.atomic():
            super().save(*args, **kwargs)
            self.order.update_status()

