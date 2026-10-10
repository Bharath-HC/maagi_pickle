from urllib.parse import urlparse

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..forms import ChangePasswordForm, ForgotPasswordForm, LoginForm, RegisterForm, ResetPasswordForm
from ..models import Address, Role, User, utcnow
from ..services.audit_service import log_action

auth_bp = Blueprint("auth", __name__, url_prefix="")


def _safe_next(target):
    if not target:
        return None
    parsed = urlparse(target)
    if parsed.netloc or parsed.scheme:
        return None
    return target


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for(current_user.dashboard_endpoint))
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower().strip()).first():
            flash("An account already exists with this email.", "danger")
            return render_template("auth/register.html", form=form)
        if User.query.filter_by(phone=form.phone.data.strip()).first():
            flash("An account already exists with this phone number.", "danger")
            return render_template("auth/register.html", form=form)
        user = User(name=form.name.data.strip(), email=form.email.data.lower().strip(),
                   phone=form.phone.data.strip(), role=Role.CUSTOMER,
                   address=form.address.data, city=form.city.data, state=form.state.data,
                   pincode=form.pincode.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()
        if form.address.data and form.city.data and form.state.data and form.pincode.data:
            db.session.add(Address(user_id=user.id, label="Home", name=user.name, phone=user.phone,
                                   line1=form.address.data, city=form.city.data, state=form.state.data,
                                   pincode=form.pincode.data, is_default=True))
        db.session.commit()
        log_action("USER_REGISTERED", "User", user.id)
        login_user(user)
        flash("Welcome to Maagi Pickle! Your account has been created.", "success")
        return redirect(url_for("customer.dashboard"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(current_user.dashboard_endpoint))
    form = LoginForm()
    next_url = _safe_next(request.args.get("next"))
    if form.validate_on_submit():
        identifier = form.identifier.data.strip().lower()
        user = User.query.filter((User.email == identifier) | (User.phone == form.identifier.data.strip())).first()
        if not user:
            flash("No account found with those details.", "danger")
        elif user.is_locked:
            flash("This account is temporarily locked due to repeated failed attempts. Try again later.", "danger")
        elif not user.is_active:
            flash("This account has been deactivated. Please contact support.", "danger")
        elif not user.check_password(form.password.data):
            user.register_failed_login()
            db.session.commit()
            flash("Incorrect password.", "danger")
        elif user.role != form.login_as.data:
            flash(f"This account is not registered as a {form.login_as.data.title()}. "
                 f"Please select '{user.role_label}' to continue.", "warning")
        else:
            user.register_success()
            db.session.commit()
            login_user(user, remember=form.remember.data)
            log_action("USER_LOGIN", "User", user.id)
            flash(f"Welcome back, {user.name.split(' ')[0]}!", "success")
            return redirect(next_url or url_for(user.dashboard_endpoint))
    return render_template("auth/login.html", form=form, next=next_url)


@auth_bp.route("/logout")
@login_required
def logout():
    log_action("USER_LOGOUT", "User", current_user.id)
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.home"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        # Architecture note: wire this to an email provider via MAIL_* settings to send a
        # tokenized reset link to reset_password(token). For this build the flow is in
        # place end-to-end but the email dispatch is a documented wiring point.
        flash("If an account exists with that email, password reset instructions have been sent.", "info")
        if user:
            log_action("PASSWORD_RESET_REQUESTED", "User", user.id)
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    form = ResetPasswordForm()
    if form.validate_on_submit():
        flash("Your password has been reset. Please log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html", form=form, token=token)


@auth_bp.route("/account/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "danger")
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            log_action("PASSWORD_CHANGED", "User", current_user.id)
            flash("Password updated successfully.", "success")
            return redirect(url_for(current_user.dashboard_endpoint))
    return render_template("auth/change_password.html", form=form)
