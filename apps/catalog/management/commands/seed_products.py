import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.models import User
from apps.catalog.models import (
    Brand,
    Category,
    Product,
    ProductImage,
    ProductVariant,
    Sport,
)
from apps.reviews.models import Review

fake = None  # lazily created in handle() so `--help` doesn't need Faker installed


# ---------------------------------------------------------------------------
# Brands
# ---------------------------------------------------------------------------

BRANDS_BY_SPORT = {
    Sport.TENNIS: ["Wilson", "Babolat", "Head", "Yonex", "Prince", "Dunlop", "Tecnifibre"],
    Sport.SQUASH: ["Dunlop", "Head", "Tecnifibre", "Prince", "Salming"],
    Sport.BADMINTON: ["Yonex", "Victor", "Li-Ning", "Babolat", "Carlton"],
    Sport.TABLE_TENNIS: ["Butterfly", "Stiga", "Donic", "Joola", "Yasaka"],
}


# ---------------------------------------------------------------------------
# Category tree: sport -> product type -> (optional) sub-type
# Each leaf is tagged with a "kind" that drives spec/variant generation.
# ---------------------------------------------------------------------------

CATEGORY_TREE = {
    Sport.TENNIS: {
        "Rackets": {
            "Power Rackets": "racket",
            "Control Rackets": "racket",
            "Tweener Rackets": "racket",
        },
        "Strings": "string",
        "Balls": "ball",
        "Bags": "bag",
        "Shoes": "shoe",
        "Apparel": "apparel",
    },
    Sport.SQUASH: {
        "Rackets": "racket",
        "Balls": "ball",
        "Eyewear": "eyewear",
        "Shoes": "shoe",
        "Bags": "bag",
    },
    Sport.BADMINTON: {
        "Rackets": "racket",
        "Shuttlecocks": "shuttlecock",
        "Shoes": "shoe",
        "Bags": "bag",
        "Apparel": "apparel",
    },
    Sport.TABLE_TENNIS: {
        "Paddles": "paddle",
        "Rubbers": "rubber",
        "Balls": "ball",
        "Tables": "table",
        "Bags": "bag",
    },
}


# ---------------------------------------------------------------------------
# Name generation
# ---------------------------------------------------------------------------

SERIES_WORDS = [
    "Pro", "Elite", "Tour", "Speed", "Power", "Control", "Aero", "Blade",
    "Extreme", "Gravity", "Burst", "Instinct", "Velocity", "Edge", "Fusion",
    "Vortex", "Strike", "Ignite", "Phantom", "Apex",
]
MODEL_NUMBERS = ["97", "98", "100", "105", "300", "500", "700", "7", "9", "12", "MP", "Lite", "X", "Team"]

GRIP_SIZES = ["L1", "L2", "L3", "L4", "L5"]
WEIGHT_CLASSES = ["3U", "4U", "5U", "6U"]
HANDLE_TYPES = ["Flared (FL)", "Straight (ST)", "Concave (CS)"]
RUBBER_COLORS = ["Red", "Black"]
STRING_COLORS = ["Natural", "Black", "Yellow", "Red", "Blue"]
BAG_COLORS = ["Black", "Navy", "Grey", "Red"]
APPAREL_SIZES = ["XS", "S", "M", "L", "XL", "XXL"]
SHOE_SIZES = [str(s) for s in range(38, 47)]
SHUTTLE_SPEEDS = ["76", "77", "78", "79"]
STRINGING_PATTERNS = ["16x19", "16x18", "18x20", "16x20"]

REVIEW_SNIPPETS = [
    "Great {noun} for the price, very happy with this purchase.",
    "Solid choice, {pro}. Would buy again.",
    "Took a few sessions to get used to it, but now {pro}.",
    "Exactly as described, delivery was fast too.",
    "{pro}. Not the best I've owned, but good value overall.",
    "My coach recommended something similar, this comes close and costs less.",
    "Comfortable and well-built. {pro}.",
    "A bit heavier than I expected, but performance is there.",
    "Perfect for intermediate players. {pro}.",
    "Been using it for a month now, holding up well.",
]
REVIEW_PROS = [
    "great control", "excellent power", "very durable", "nice touch and feel",
    "good spin potential", "lightweight and manoeuvrable", "great value for money",
    "premium build quality",
]


def make_name(brand_name):
    series = random.choice(SERIES_WORDS)
    number = random.choice(MODEL_NUMBERS)
    return f"{brand_name} {series} {number}"


def unique_slug(model_cls, base):
    slug = slugify(base)
    candidate = slug
    i = 1
    while model_cls.objects.filter(slug=candidate).exists():
        i += 1
        candidate = f"{slug}-{i}"
    return candidate


# ---------------------------------------------------------------------------
# Per-kind spec / variant / price generation
# ---------------------------------------------------------------------------

def specs_for(kind, sport):
    if kind == "racket":
        specs = {
            "weight_g": random.choice([260, 275, 285, 300, 310, 320]),
            "balance_point_mm": random.choice([310, 320, 325, 330, 335]),
            "stiffness_ra": random.choice([58, 62, 65, 68, 70]),
        }
        if sport == Sport.TENNIS:
            specs["head_size_sq_in"] = random.choice([95, 98, 100, 105, 107])
            specs["string_pattern"] = random.choice(STRINGING_PATTERNS)
        elif sport == Sport.SQUASH:
            specs["head_size_sq_in"] = random.choice([65, 70, 73, 75])
            specs["string_pattern"] = random.choice(["14x18", "14x19"])
        elif sport == Sport.BADMINTON:
            specs["flex"] = random.choice(["Flexible", "Medium", "Stiff"])
            specs["balance"] = random.choice(["Head Heavy", "Even Balance", "Head Light"])
        return specs
    if kind == "paddle":
        return {
            "blade_material": random.choice(["All-wood", "Carbon composite", "Ayous/Carbon"]),
            "speed_rating": random.randint(6, 10),
            "spin_rating": random.randint(6, 10),
            "control_rating": random.randint(6, 10),
            "handle_type": random.choice(HANDLE_TYPES),
        }
    if kind == "rubber":
        return {
            "sponge_thickness_mm": random.choice([1.8, 2.0, 2.1, "Max"]),
            "speed": random.randint(6, 10),
            "spin": random.randint(6, 10),
            "control": random.randint(6, 10),
        }
    if kind == "string":
        return {
            "gauge_mm": random.choice([1.20, 1.25, 1.30, 1.35]),
            "material": random.choice(["Polyester", "Natural gut", "Synthetic gut", "Multifilament"]),
            "recommended_tension_lbs": f"{random.randint(45, 55)}-{random.randint(56, 65)}",
        }
    if kind == "ball":
        return {
            "pack_size": random.choice([3, 4, 6, 12]),
            "material": "Rubber/felt composite" if sport != Sport.TABLE_TENNIS else "ABS plastic",
        }
    if kind == "bag":
        return {
            "capacity_l": random.choice([15, 25, 35, 45]),
            "compartments": random.randint(1, 4),
            "material": random.choice(["Polyester", "Nylon ripstop", "Thermal-lined polyester"]),
        }
    if kind == "shoe":
        return {
            "upper_material": random.choice(["Mesh", "Synthetic leather", "Knit"]),
            "sole_type": random.choice(["Herringbone", "Gum rubber", "Multi-court"]),
            "weight_g": random.choice([280, 310, 340, 360]),
        }
    if kind == "apparel":
        return {
            "material": random.choice(["Polyester", "Cotton blend", "Recycled polyester"]),
            "fit": random.choice(["Regular", "Slim", "Athletic"]),
        }
    if kind == "eyewear":
        return {
            "lens_type": random.choice(["Clear", "Anti-fog", "Polarized"]),
            "uv_protection": True,
        }
    if kind == "shuttlecock":
        return {
            "material": random.choice(["Goose feather", "Nylon"]),
            "speed_rating": random.choice(SHUTTLE_SPEEDS),
        }
    if kind == "table":
        return {
            "thickness_mm": random.choice([16, 19, 22, 25]),
            "foldable": random.choice([True, False]),
            "indoor_outdoor": random.choice(["Indoor", "Outdoor"]),
        }
    return {}


def price_range_for(kind):
    return {
        "racket": (280, 1400),
        "paddle": (60, 450),
        "rubber": (60, 320),
        "string": (25, 140),
        "ball": (15, 70),
        "bag": (90, 550),
        "shoe": (180, 650),
        "apparel": (60, 320),
        "eyewear": (90, 260),
        "shuttlecock": (60, 180),
        "table": (900, 6500),
    }.get(kind, (50, 300))


def variant_dimension_for(kind, sport):
    if kind == "racket":
        if sport == Sport.TENNIS:
            return "grip_size", GRIP_SIZES
        if sport == Sport.BADMINTON:
            return "weight_class", WEIGHT_CLASSES
        return "color", BAG_COLORS
    if kind == "paddle":
        return "handle_type", HANDLE_TYPES
    if kind == "rubber":
        return "color", RUBBER_COLORS
    if kind == "string":
        return "color", STRING_COLORS
    if kind == "bag":
        return "color", BAG_COLORS
    if kind == "shoe":
        return "shoe_size", SHOE_SIZES
    if kind == "apparel":
        return "apparel_size", APPAREL_SIZES
    if kind == "shuttlecock":
        return "speed_rating", SHUTTLE_SPEEDS
    return None, None


def to_currency(pln_amount, rate):
    return (Decimal(pln_amount) / Decimal(str(rate))).quantize(Decimal("0.01"))


EUR_RATE = "4.30"
USD_RATE = "3.95"


class Command(BaseCommand):
    help = "Seed the catalog with realistic demo data across tennis, squash, badminton, and table tennis."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush", action="store_true",
            help="Delete previously seeded catalog/review/demo-user data before seeding.",
        )
        parser.add_argument(
            "--products-per-category", type=int, default=5,
            help="How many products to generate per leaf category (default: 5).",
        )
        parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible output.")

    def handle(self, *args, **options):
        global fake
        from faker import Faker

        fake = Faker()
        if options["seed"] is not None:
            random.seed(options["seed"])
            Faker.seed(options["seed"])

        if options["flush"]:
            self.flush_demo_data()

        with transaction.atomic():
            brands = self.create_brands()
            categories = self.create_categories()
            products = self.create_products(brands, categories, options["products_per_category"])
            users = self.create_demo_users()
            self.create_reviews(products, users)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(products)} products across {len(categories)} categories, "
            f"{len(users)} demo users, and reviews."
        ))

    # -- flush -------------------------------------------------------------

    def flush_demo_data(self):
        self.stdout.write("Flushing previously seeded catalog/review data...")
        Review.objects.all().delete()
        ProductImage.objects.all().delete()
        ProductVariant.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        Brand.objects.all().delete()
        User.objects.filter(is_superuser=False, is_staff=False).delete()

    # -- brands --------------------------------------------------------------

    def create_brands(self):
        names = sorted({name for names in BRANDS_BY_SPORT.values() for name in names})
        brands = {}
        for name in names:
            brand, _ = Brand.objects.get_or_create(name=name, defaults={"slug": slugify(name)})
            brands[name] = brand
        self.stdout.write(f"Brands: {len(brands)}")
        return brands

    # -- categories ------------------------------------------------------------

    def create_categories(self):
        leaves = {}  # slug -> (Category, sport, kind)
        for sport, tree in CATEGORY_TREE.items():
            sport_label = dict(Sport.choices)[sport]
            sport_cat, _ = Category.objects.get_or_create(
                slug=slugify(sport_label), defaults={"name": sport_label}
            )
            for type_name, sub in tree.items():
                if isinstance(sub, dict):
                    type_cat, _ = Category.objects.get_or_create(
                        slug=slugify(f"{sport_label}-{type_name}"),
                        defaults={"name": type_name, "parent": sport_cat},
                    )
                    for subtype_name, kind in sub.items():
                        leaf, _ = Category.objects.get_or_create(
                            slug=slugify(f"{sport_label}-{type_name}-{subtype_name}"),
                            defaults={"name": subtype_name, "parent": type_cat},
                        )
                        leaves[leaf.slug] = (leaf, sport, kind)
                else:
                    kind = sub
                    leaf, _ = Category.objects.get_or_create(
                        slug=slugify(f"{sport_label}-{type_name}"),
                        defaults={"name": type_name, "parent": sport_cat},
                    )
                    leaves[leaf.slug] = (leaf, sport, kind)
        self.stdout.write(f"Categories (leaf): {len(leaves)}")
        return leaves

    # -- products ------------------------------------------------------------

    def create_products(self, brands, categories, count_per_category):
        products = []
        now = timezone.now()

        for leaf_slug, (category, sport, kind) in categories.items():
            brand_names = BRANDS_BY_SPORT[sport]
            lo, hi = price_range_for(kind)
            variant_dim, variant_options = variant_dimension_for(kind, sport)

            for _ in range(count_per_category):
                brand_name = random.choice(brand_names)
                brand = brands[brand_name]
                name = make_name(brand_name)
                slug = unique_slug(Product, name)

                price_pln = Decimal(random.randrange(lo, hi, 5))
                on_sale = random.random() < 0.18
                sale_price_pln = None
                sale_start = sale_end = None
                if on_sale:
                    sale_price_pln = (price_pln * Decimal(random.choice(["0.70", "0.75", "0.80", "0.85"]))).quantize(Decimal("1"))
                    offset = random.choice([-10, -3, 0, 2, 5])
                    sale_start = now + timedelta(days=offset)
                    sale_end = sale_start + timedelta(days=random.randint(7, 21))

                product = Product.objects.create(
                    name=name,
                    slug=slug,
                    description=self.make_description(kind, name),
                    sport=sport,
                    category=category,
                    brand=brand,
                    vat_rate=random.choices([23, 8], weights=[85, 15])[0],
                    price_pln=price_pln,
                    price_eur=to_currency(price_pln, EUR_RATE),
                    price_usd=to_currency(price_pln, USD_RATE),
                    sale_price_pln=sale_price_pln,
                    sale_price_eur=to_currency(sale_price_pln, EUR_RATE) if sale_price_pln else None,
                    sale_price_usd=to_currency(sale_price_pln, USD_RATE) if sale_price_pln else None,
                    sale_start=sale_start,
                    sale_end=sale_end,
                    specs=specs_for(kind, sport),
                    meta_title=name,
                    meta_description=f"{name} - shop {category.name.lower()} at Racket Sports Shop.",
                )
                self.create_variants(product, kind, variant_dim, variant_options)
                products.append(product)

        self.stdout.write(f"Products: {len(products)}")
        return products

    def make_description(self, kind, name):
        blurbs = {
            "racket": "Precision-engineered for players who demand consistency on every swing.",
            "paddle": "Balanced blade and rubber combination for all-round attacking play.",
            "rubber": "High-grip rubber sheet tuned for spin and speed off the blade.",
            "string": "Reliable string built to hold tension and feel through long rallies.",
            "ball": "Match-grade balls with consistent bounce and durability.",
            "bag": "Spacious, well-organised bag built for daily training and travel.",
            "shoe": "Supportive court shoe designed for quick lateral movement.",
            "apparel": "Breathable performance wear built to move with you on court.",
            "eyewear": "Impact-resistant eyewear for safer, clearer play.",
            "shuttlecock": "Consistent flight shuttlecocks for club and tournament play.",
            "table": "Tournament-standard table built for durable, consistent bounce.",
        }
        return f"{name}. {blurbs.get(kind, 'Quality equipment for players of all levels.')}"

    def create_variants(self, product, kind, variant_dim, variant_options):
        if variant_dim is None:
            ProductVariant.objects.create(
                product=product,
                attributes={},
                stock_quantity=random.choice([0, 0, 5, 12, 25, 40]),
            )
            return

        chosen = random.sample(variant_options, k=min(len(variant_options), random.randint(2, len(variant_options))))
        for option in chosen:
            ProductVariant.objects.create(
                product=product,
                attributes={variant_dim: option},
                stock_quantity=random.choice([0, 0, 3, 8, 15, 30, 50]),
            )

    # -- users ---------------------------------------------------------------

    def create_demo_users(self):
        users = []
        for _ in range(15):
            first = fake.first_name()
            last = fake.last_name()
            username = slugify(f"{first}.{last}.{random.randint(1, 9999)}")
            email = f"{username}@example.com"
            user = User.objects.create_user(
                username=username,
                email=email,
                password="demo-pass-123",
                first_name=first,
                last_name=last,
            )
            users.append(user)
        self.stdout.write(f"Demo users: {len(users)}")
        return users

    # -- reviews ---------------------------------------------------------------

    def create_reviews(self, products, users):
        count = 0
        for product in products:
            if random.random() > 0.55:
                continue
            reviewers = random.sample(users, k=min(len(users), random.randint(1, 4)))
            for user in reviewers:
                rating = random.choices([5, 4, 3, 2], weights=[45, 35, 15, 5])[0]
                template = random.choice(REVIEW_SNIPPETS)
                comment = template.format(
                    noun=random.choice(["racket", "product", "piece of kit"]),
                    pro=random.choice(REVIEW_PROS),
                )
                Review.objects.create(
                    product=product,
                    user=user,
                    rating=rating,
                    comment=comment,
                    verified_purchase=random.random() < 0.7,
                )
                count += 1
            reviews = list(product.reviews.all())
            product.review_count = len(reviews)
            product.average_rating = (
                round(sum(r.rating for r in reviews) / len(reviews), 2) if reviews else 0
            )
            product.save(update_fields=["review_count", "average_rating"])
        self.stdout.write(f"Reviews: {count}")
