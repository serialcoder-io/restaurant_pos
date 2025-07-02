from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='images/category')

    class Meta:
        db_table = 'category'
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return f"Category: {self.name}"


class Product(models.Model):
    category = models.ManyToManyField(Category, related_name='products')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='images/products')
    price = models.DecimalField(decimal_places=2, max_digits=8)  # plus large max_digits si besoin
    is_available = models.BooleanField(default=True)

    class Meta:
        db_table = 'product'
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        return f"Product: {self.name}"


class Menu(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    class Meta:
        db_table = 'menu'
        verbose_name = "Menu"
        verbose_name_plural = "Menus"

    def __str__(self):
        return f"Menu: {self.name}"


class MenuVariant(models.Model):
    size = models.CharField(max_length=100)
    price = models.DecimalField(decimal_places=2, max_digits=8)
    image = models.ImageField(upload_to='images/menus')
    is_available = models.BooleanField(default=True)

    class Meta:
        db_table = 'menu_variant'
        verbose_name = "Menu Variant"
        verbose_name_plural = "Menu Variants"

    def __str__(self):
        return f"{self.size} - {self.price} Rs"
