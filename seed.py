"""Seed the Maagi Pickle database with demo accounts, products and sample data.

Run with:  flask seed   (after setting FLASK_APP=run.py)
or:        python seed.py
"""
import os
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def get_or_create_user(db, User, Role, email, **kwargs):
    user = User.query.filter_by(email=email).first()
    if user:
        return user, False
    password = kwargs.pop("password")
    user = User(email=email, **kwargs)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    return user, True


def run_seed(app):
    from app.extensions import db
    from app.models import (Address, Banner, Category, Coupon, Product, ProductImage,
                            ProductVariant, Role, User, utcnow)

    with app.app_context():
        db.create_all()
        demo_password = app.config.get("DEMO_PASSWORD", "Maagi@12345")

        admin, _ = get_or_create_user(db, User, Role, "admin@maagi.local", name="Maagi Admin",
                                      phone="9000000001", role=Role.ADMIN, password=demo_password)
        distributor, _ = get_or_create_user(db, User, Role, "distributor@maagi.local", name="Demo Distributor",
                                            phone="9000000002", role=Role.DISTRIBUTOR, password=demo_password,
                                            company_name="Demo Distribution Co.", gst_number="29DEMODIST1Z5")
        wholesaler, _ = get_or_create_user(db, User, Role, "wholesaler@maagi.local", name="Demo Wholesaler",
                                           phone="9000000003", role=Role.WHOLESALER, password=demo_password,
                                           company_name="Demo Wholesale Traders", gst_number="29DEMOWHOL1Z5")
        customer, created = get_or_create_user(db, User, Role, "customer@maagi.local", name="Demo Customer",
                                               phone="9000000004", role=Role.CUSTOMER, password=demo_password,
                                               city="Bengaluru", state="Karnataka", pincode="560001")
        db.session.commit()

        if created and not customer.addresses.first():
            db.session.add(Address(user_id=customer.id, label="Home", name=customer.name, phone=customer.phone,
                                   line1="12, MG Road", city="Bengaluru", state="Karnataka", pincode="560001",
                                   is_default=True))
            db.session.commit()

        categories = {}
        for name, desc, image in [
            ("Specialty Pickles", "Our signature dry fruit and lemon chilli pickles.", "images/categories/specialty.webp"),
            ("Vegetable Pickles", "Traditional mango and mixed vegetable pickles.", "images/categories/traditional-bowls.webp"),
            ("Bulk Packs", "Larger pack sizes for business and bulk buyers.", "images/categories/bulk-packs.webp"),
        ]:
            cat = Category.query.filter_by(name=name).first()
            if not cat:
                from app.utils.helpers import slugify
                cat = Category(name=name, slug=slugify(name), description=desc, image=image, active=True)
                db.session.add(cat)
                db.session.flush()
            categories[name] = cat
        db.session.commit()

        def make_product(name, slug, category, short_desc, description, image_base, sku, gst, variants):
            product = Product.query.filter_by(slug=slug).first()
            if product:
                return product
            product = Product(
                name=name, slug=slug, category_id=category.id, short_description=short_desc,
                description=description, ingredients="Mixed spices, edible oil, salt, and natural preservatives.",
                nutritional_information="Approx. 180 kcal per 100g (values vary by batch; demo data).",
                shelf_life="9 months from date of packing when stored correctly.",
                storage_instructions="Store in a cool, dry place away from direct sunlight. Refrigerate after opening.",
                manufacturer="Prashanth Home Industries", sku=sku, hsn_code="2001", gst_percentage=gst,
                minimum_order_quantity=10, featured=True, active=True, is_demo=True,
            )
            db.session.add(product)
            db.session.flush()
            db.session.add(ProductImage(product_id=product.id, path=f"images/products/{image_base}-range.webp", sort_order=0))
            for weight, unit, sku_suffix, mrp, cust, whole, dist, stock, img_suffix in variants:
                db.session.add(ProductVariant(
                    product_id=product.id, weight=weight, unit=unit, sku=f"{sku}-{sku_suffix}",
                    mrp=mrp, customer_price=cust, wholesaler_price=whole, distributor_price=dist,
                    stock_quantity=stock, min_stock_level=10, reorder_level=25, active=True,
                    image=f"images/products/{image_base}-{img_suffix}.webp",
                ))
            db.session.commit()
            product.sync_stock()
            db.session.commit()
            return product

        # NOTE: All prices below are illustrative DEMO data for seeding/testing only —
        # they are NOT official Maagi Pickle retail prices. Update via the admin panel.
        make_product(
            "Dry Fruit Pickle", "dry-fruit-pickle", categories["Specialty Pickles"],
            "A rich, indulgent pickle blended with premium dry fruits.",
            "Maagi's Dry Fruit Pickle brings together a rich mix of premium dry fruits and traditional spices, "
            "slow-prepared the way it's always been done in Prashanth Home Industries' kitchens.",
            "dry-fruit-pickle", "MAAGI-DFP", 12,
            [
                (200, "g", "200G", 180, 160, 140, 130, 60, "200g"),
                (500, "g", "500G", 420, 380, 340, 320, 45, "500g"),
                (1, "kg", "1KG", 780, 720, 650, 610, 30, "1kg"),
                (5, "kg", "5KG", 3600, 3400, 3100, 2900, 4, "5kg"),
            ],
        )
        make_product(
            "Lemon Chilli Pickle", "lemon-chilli-pickle", categories["Specialty Pickles"],
            "Tangy lemons with a fiery chilli kick — a true classic.",
            "A zesty, fiery classic — fresh lemons pickled with hand-ground chillies and spices for a tangy, "
            "bold flavour that pairs with everything from rice to parathas.",
            "lemon-chilli-pickle", "MAAGI-LCP", 12,
            [
                (200, "g", "200G", 140, 120, 105, 98, 80, "200g"),
                (500, "g", "500G", 320, 290, 260, 245, 60, "500g"),
                (1, "kg", "1KG", 600, 550, 500, 470, 40, "1kg"),
                (5, "kg", "5KG", 2800, 2650, 2400, 2250, 12, "5kg"),
            ],
        )
        make_product(
            "Mango Pickle", "mango-pickle", categories["Vegetable Pickles"],
            "The timeless favourite — raw mango pickled in traditional masala.",
            "Our Mango Pickle is prepared with raw mangoes and a traditional blend of mustard, fenugreek and "
            "chilli, pickled slowly for that unmistakable tangy-spicy flavour.",
            "mango-pickle", "MAAGI-MGP", 12,
            [
                (200, "g", "200G", 130, 110, 98, 92, 90, "200g"),
                (500, "g", "500G", 290, 260, 235, 220, 70, "500g"),
                (1, "kg", "1KG", 540, 495, 450, 420, 50, "1kg"),
                (2, "kg", "2KG", 1040, 960, 870, 820, 25, "2kg"),
                (5, "kg", "5KG", 2500, 2350, 2150, 2000, 10, "5kg"),
            ],
        )
        make_product(
            "Mixed Veg Pickle", "mixed-veg-pickle", categories["Vegetable Pickles"],
            "A colourful medley of seasonal vegetables in classic pickle masala.",
            "A vibrant combination of carrots, green chillies and seasonal vegetables, pickled together in "
            "our classic home-style masala.",
            "mixed-veg-pickle", "MAAGI-MVP", 12,
            [
                (200, "g", "200G", 120, 105, 92, 86, 75, "200g"),
                (500, "g", "500G", 270, 245, 220, 205, 55, "500g"),
                (1, "kg", "1KG", 500, 460, 415, 390, 35, "1kg"),
                (2, "kg", "2KG", 960, 890, 810, 760, 20, "2kg"),
                (5, "kg", "5KG", 2300, 2180, 1990, 1860, 4, "5kg"),  # deliberately low stock
            ],
        )

        if not Coupon.query.filter_by(code="MAAGI10").first():
            db.session.add(Coupon(code="MAAGI10", description="10% off on your first order",
                                  discount_type="PERCENT", discount_value=10, min_order=299, max_discount=150,
                                  start_date=utcnow() - timedelta(days=1), expiry_date=utcnow() + timedelta(days=365),
                                  usage_limit=500, per_user_limit=1, customers_only=True, active=True))

        if not Banner.query.first():
            db.session.add(Banner(title="The True Taste of Tradition", subtitle="Authentic pickles, crafted since 2001",
                                  image="images/banners/hero-landscape.webp", link="/products/", cta_label="Shop Now",
                                  sort_order=0, active=True))

        db.session.commit()

        print("\n" + "=" * 60)
        print("Maagi Pickle — database seeded successfully")
        print("=" * 60)
        print(f"  Admin:        admin@maagi.local       / {demo_password}")
        print(f"  Distributor:  distributor@maagi.local / {demo_password}")
        print(f"  Wholesaler:   wholesaler@maagi.local   / {demo_password}")
        print(f"  Customer:     customer@maagi.local     / {demo_password}")
        print("=" * 60)
        print("  NOTE: These are DEV-ONLY demo accounts and prices. Do not use in production.")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    from app import create_app
    app = create_app(os.getenv("FLASK_ENV", "development"))
    run_seed(app)
