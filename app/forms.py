from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (BooleanField, DateField, DecimalField, HiddenField, IntegerField,
                     PasswordField, RadioField, SelectField, StringField, TextAreaField)
from wtforms.validators import (DataRequired, EqualTo, Length, NumberRange,
                                Optional, Regexp, ValidationError)

PHONE_RE = Regexp(r"^[0-9+\-\s]{7,15}$", message="Enter a valid phone number.")
PIN_RE = Regexp(r"^\d{6}$", message="Enter a valid 6-digit pincode.")
# A lightweight, syntax-only email check. We deliberately avoid wtforms' Email
# validator (backed by the `email_validator` package), which rejects
# special-use/reserved-looking domains such as the `*.local` addresses used by
# this project's demo accounts (admin@maagi.local, etc.) even though they are
# syntactically valid email addresses for a self-hosted dev/demo environment.
Email = Regexp(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", message="Enter a valid email address.")


class LoginForm(FlaskForm):
    identifier = StringField("Email or Mobile Number", validators=[DataRequired(), Length(max=160)])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")
    login_as = RadioField(
        "Login as",
        choices=[("CUSTOMER", "Customer"), ("WHOLESALER", "Wholesaler"),
                 ("DISTRIBUTOR", "Distributor"), ("ADMIN", "Admin")],
        default="CUSTOMER",
    )


class RegisterForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email, Length(max=160)])
    phone = StringField("Mobile Number", validators=[DataRequired(), PHONE_RE])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, message="Use at least 8 characters.")])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password", message="Passwords must match.")])
    address = StringField("Address", validators=[Optional(), Length(max=255)])
    city = StringField("City", validators=[Optional(), Length(max=80)])
    state = StringField("State", validators=[Optional(), Length(max=80)])
    pincode = StringField("Pincode", validators=[Optional(), PIN_RE])
    agree = BooleanField("I agree to the Terms & Conditions", validators=[DataRequired(message="Please accept the terms to continue.")])


class ForgotPasswordForm(FlaskForm):
    email = StringField("Registered Email", validators=[DataRequired(), Email])


class ResetPasswordForm(FlaskForm):
    password = PasswordField("New Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])


class ProfileForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    phone = StringField("Mobile Number", validators=[DataRequired(), PHONE_RE])
    company_name = StringField("Company Name", validators=[Optional(), Length(max=160)])
    gst_number = StringField("GST Number", validators=[Optional(), Length(max=20)])
    address = StringField("Address", validators=[Optional(), Length(max=255)])
    city = StringField("City", validators=[Optional(), Length(max=80)])
    state = StringField("State", validators=[Optional(), Length(max=80)])
    pincode = StringField("Pincode", validators=[Optional(), PIN_RE])


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField("Confirm New Password", validators=[DataRequired(), EqualTo("new_password")])


class AddressForm(FlaskForm):
    label = StringField("Label (e.g. Home, Office)", validators=[Optional(), Length(max=40)])
    name = StringField("Recipient Name", validators=[DataRequired(), Length(max=120)])
    phone = StringField("Phone", validators=[DataRequired(), PHONE_RE])
    line1 = StringField("Address Line 1", validators=[DataRequired(), Length(max=200)])
    line2 = StringField("Address Line 2", validators=[Optional(), Length(max=200)])
    city = StringField("City", validators=[DataRequired(), Length(max=80)])
    state = StringField("State", validators=[DataRequired(), Length(max=80)])
    pincode = StringField("Pincode", validators=[DataRequired(), PIN_RE])
    is_default = BooleanField("Set as default address")


class ContactForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email])
    phone = StringField("Phone", validators=[Optional(), PHONE_RE])
    subject = StringField("Subject", validators=[DataRequired(), Length(max=160)])
    message = TextAreaField("Message", validators=[DataRequired(), Length(max=2000)])


class NewsletterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email])


class ReviewForm(FlaskForm):
    rating = SelectField("Rating", choices=[(str(i), f"{i} Star{'s' if i > 1 else ''}") for i in range(5, 0, -1)],
                         validators=[DataRequired()])
    title = StringField("Review Title", validators=[DataRequired(), Length(max=120)])
    body = TextAreaField("Your Review", validators=[Optional(), Length(max=2000)])


class B2BApplicationForm(FlaskForm):
    name = StringField("Contact Name", validators=[DataRequired(), Length(max=120)])
    company_name = StringField("Company Name", validators=[DataRequired(), Length(max=160)])
    phone = StringField("Phone", validators=[DataRequired(), PHONE_RE])
    email = StringField("Email", validators=[DataRequired(), Email])
    address = StringField("Address", validators=[DataRequired(), Length(max=255)])
    city = StringField("City", validators=[DataRequired(), Length(max=80)])
    state = StringField("State", validators=[DataRequired(), Length(max=80)])
    pincode = StringField("Pincode", validators=[DataRequired(), PIN_RE])
    gst_number = StringField("GST Number", validators=[Optional(), Length(max=20)])
    business_type = SelectField(
        "Business Type",
        choices=[("Retailer", "Retailer"), ("Restaurant/Hotel", "Restaurant / Hotel"),
                 ("Wholesaler", "Wholesaler"), ("Distributor", "Distributor"), ("Other", "Other")],
    )
    expected_monthly_purchase = SelectField(
        "Expected Monthly Purchase",
        choices=[("Under Rs 25,000", "Under ₹25,000"), ("Rs 25,000 - Rs 1,00,000", "₹25,000 - ₹1,00,000"),
                 ("Rs 1,00,000 - Rs 5,00,000", "₹1,00,000 - ₹5,00,000"), ("Above Rs 5,00,000", "Above ₹5,00,000")],
    )
    role = HiddenField(default="DISTRIBUTOR")


class BulkOrderForm(FlaskForm):
    name = StringField("Your Name", validators=[DataRequired(), Length(max=120)])
    company_name = StringField("Company Name", validators=[Optional(), Length(max=160)])
    email = StringField("Email", validators=[DataRequired(), Email])
    phone = StringField("Phone", validators=[DataRequired(), PHONE_RE])
    gst_number = StringField("GST Number", validators=[Optional(), Length(max=20)])
    delivery_address = TextAreaField("Delivery Address", validators=[DataRequired(), Length(max=300)])
    expected_delivery_date = DateField("Expected Delivery Date", validators=[Optional()])
    message = TextAreaField("Tell us what you need", validators=[Optional(), Length(max=1000)])


class SupportTicketForm(FlaskForm):
    category = SelectField("Category", choices=[("GENERAL", "General"), ("ORDER", "Order Issue"),
                                                 ("PAYMENT", "Payment Issue"), ("STOCK_REQUEST", "Stock Request")])
    subject = StringField("Subject", validators=[DataRequired(), Length(max=160)])
    message = TextAreaField("Message", validators=[DataRequired(), Length(max=2000)])


class CategoryForm(FlaskForm):
    name = StringField("Category Name", validators=[DataRequired(), Length(max=100)])
    description = StringField("Description", validators=[Optional(), Length(max=300)])
    image = FileField("Category Image", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])])
    sort_order = IntegerField("Sort Order", default=0, validators=[Optional()])
    active = BooleanField("Active", default=True)


class ProductForm(FlaskForm):
    name = StringField("Product Name", validators=[DataRequired(), Length(max=160)])
    category_id = SelectField("Category", coerce=int, validators=[DataRequired()])
    short_description = StringField("Short Description", validators=[Optional(), Length(max=300)])
    description = TextAreaField("Full Description", validators=[Optional()])
    ingredients = TextAreaField("Ingredients", validators=[Optional()])
    nutritional_information = TextAreaField("Nutritional Information (per 100g)", validators=[Optional()])
    shelf_life = StringField("Shelf Life", validators=[Optional(), Length(max=120)])
    storage_instructions = TextAreaField("Storage Instructions", validators=[Optional()])
    manufacturer = StringField("Manufacturer", validators=[Optional(), Length(max=200)])
    sku = StringField("Product SKU", validators=[DataRequired(), Length(max=60)])
    hsn_code = StringField("HSN Code", validators=[Optional(), Length(max=12)])
    gst_percentage = DecimalField("GST %", validators=[DataRequired(), NumberRange(min=0, max=28)])
    minimum_order_quantity = IntegerField("Minimum Order Quantity", default=1, validators=[DataRequired(), NumberRange(min=1)])
    featured = BooleanField("Featured on Homepage")
    active = BooleanField("Active", default=True)
    image = FileField("Primary Product Image", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])])


class VariantForm(FlaskForm):
    weight = DecimalField("Weight", validators=[DataRequired(), NumberRange(min=0.01)])
    unit = SelectField("Unit", choices=[("g", "grams"), ("kg", "kg")], default="g")
    sku = StringField("Variant SKU", validators=[DataRequired(), Length(max=60)])
    mrp = DecimalField("MRP (₹)", validators=[DataRequired(), NumberRange(min=0)])
    customer_price = DecimalField("Customer Price (₹)", validators=[DataRequired(), NumberRange(min=0)])
    wholesaler_price = DecimalField("Wholesaler Price (₹)", validators=[DataRequired(), NumberRange(min=0)])
    distributor_price = DecimalField("Distributor Price (₹)", validators=[DataRequired(), NumberRange(min=0)])
    stock_quantity = IntegerField("Stock Quantity", default=0, validators=[DataRequired(), NumberRange(min=0)])
    min_stock_level = IntegerField("Minimum Stock Level", default=10, validators=[Optional(), NumberRange(min=0)])
    reorder_level = IntegerField("Reorder Level", default=25, validators=[Optional(), NumberRange(min=0)])
    image = FileField("Variant Image (optional)", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])])
    active = BooleanField("Active", default=True)

    def validate_customer_price(self, field):
        if self.mrp.data is not None and field.data is not None and field.data > self.mrp.data:
            raise ValidationError("Customer price cannot be higher than MRP.")


class CouponForm(FlaskForm):
    code = StringField("Coupon Code", validators=[DataRequired(), Length(max=40)])
    description = StringField("Description", validators=[Optional(), Length(max=200)])
    discount_type = SelectField("Discount Type", choices=[("PERCENT", "Percentage"), ("FIXED", "Fixed Amount")])
    discount_value = DecimalField("Discount Value", validators=[DataRequired(), NumberRange(min=0)])
    min_order = DecimalField("Minimum Order Amount", default=0, validators=[Optional(), NumberRange(min=0)])
    max_discount = DecimalField("Maximum Discount", validators=[Optional(), NumberRange(min=0)])
    start_date = DateField("Start Date", validators=[Optional()])
    expiry_date = DateField("Expiry Date", validators=[Optional()])
    usage_limit = IntegerField("Total Usage Limit", validators=[Optional(), NumberRange(min=1)])
    per_user_limit = IntegerField("Per-User Limit", default=1, validators=[Optional(), NumberRange(min=1)])
    active = BooleanField("Active", default=True)


class OrderStatusForm(FlaskForm):
    order_status = SelectField("Order Status")
    note = StringField("Note (optional)", validators=[Optional(), Length(max=200)])


class BannerForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=140)])
    subtitle = StringField("Subtitle", validators=[Optional(), Length(max=240)])
    image = FileField("Banner Image", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])])
    link = StringField("Link URL", validators=[Optional(), Length(max=255)])
    cta_label = StringField("Button Label", validators=[Optional(), Length(max=40)])
    sort_order = IntegerField("Sort Order", default=0, validators=[Optional()])
    active = BooleanField("Active", default=True)


class B2BReviewForm(FlaskForm):
    action = HiddenField(validators=[DataRequired()])
    admin_notes = StringField("Notes", validators=[Optional(), Length(max=300)])
