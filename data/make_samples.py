"""Generates the four sample datasets (mirroring the cookbook notebooks)."""

from pathlib import Path

HERE = Path(__file__).parent


def make_sales() -> Path:
    import random
    rng = random.Random(7)
    products = {
        "Laptop Pro": ("electronics", 1299.0), "Wireless Mouse": ("electronics", 29.99),
        "Standing Desk": ("furniture", 449.0), "Office Chair": ("furniture", 289.0),
        "USB-C Hub": ("electronics", 59.99), "Desk Lamp": ("furniture", 39.99),
        "Notebook Set": ("stationery", 12.5), "Fountain Pen": ("stationery", 45.0),
    }
    regions = ["North", "South", "East", "West"]
    rows = ["order_id,customer_id,product,category,price,quantity,order_date,region"]
    for i in range(1, 51):
        product = rng.choice(list(products))
        cat, price = products[product]
        # repeat-customer signal: 15 customers across 50 orders
        cust = f"CUST{rng.randint(1, 15):03d}"
        rows.append(f"ORD{i:04d},{cust},{product},{cat},{price},"
                    f"{rng.randint(1, 4)},2024-{rng.randint(1, 6):02d}-{rng.randint(1, 28):02d},"
                    f"{rng.choice(regions)}")
    p = HERE / "sales_data.csv"
    p.write_text("\n".join(rows) + "\n")
    return p


def make_churn() -> Path:
    import math
    import random
    rng = random.Random(42)
    rows = ["customer_id,tenure_months,support_tickets,monthly_charge,contract,favorite_color,churned"]
    for i in range(400):
        tenure = rng.randint(1, 72)
        tickets = min(10, int(rng.expovariate(0.5)))
        monthly = round(rng.gauss(60, 20), 2)
        contract = rng.choices(["month-to-month", "one-year", "two-year"], [0.5, 0.3, 0.2])[0]
        logit = -0.04 * tenure + 0.45 * tickets + (1.2 if contract == "month-to-month" else 0) - 1.0
        churned = 1 if rng.random() < 1 / (1 + math.exp(-logit)) else 0
        color = rng.choice(["red", "blue", "green"])
        rows.append(f"C{i:04d},{tenure},{tickets},{monthly},{contract},{color},{churned}")
    p = HERE / "churn_data.csv"
    p.write_text("\n".join(rows) + "\n")
    return p


def make_houses() -> Path:
    import random
    rng = random.Random(42)
    premium = {"springfield": 1.0, "shelbyville": 1.25, "ogdenville": 0.8}
    rows = ["sqft,bedrooms,city,year_built,price"]
    for _ in range(600):
        sqft = rng.randint(450, 4200)
        beds = rng.randint(1, 5)
        city = rng.choices(list(premium), [0.5, 0.3, 0.2])[0]
        year = rng.randint(1950, 2023)
        price = (sqft * 180 + beds * 9000 + (year - 1950) * 350) * premium[city]
        price = round(price * rng.gauss(1.0, 0.08), -2)
        rows.append(f"{sqft},{beds},{city},{year},{price}")
    p = HERE / "houses.csv"
    p.write_text("\n".join(rows) + "\n")
    return p


def make_faq() -> Path:
    p = HERE / "acme_faq.md"
    p.write_text("""\
# Acme Cloud — Product FAQ

## Billing
Acme Cloud bills per second of compute with a 60-second minimum.
Invoices are issued on the 1st of each month. Enterprise plans can
switch to annual invoicing by contacting billing@acme.example.

## Limits
Free tier: 2 vCPUs, 4 GB RAM, 10 GB storage, 100 GB egress per month.
Pro tier: 32 vCPUs, 128 GB RAM, 2 TB storage, 5 TB egress per month.
Limits reset at 00:00 UTC on the first day of the billing cycle.

## Regions
Acme Cloud runs in us-east-1, eu-west-2, and ap-south-1. Data at rest
never leaves the region you select. Cross-region replication is a Pro
feature and doubles storage cost.

## Support
Free tier gets community support. Pro tier gets 24/7 chat with a
4-hour first-response SLA. Severity-1 incidents for Enterprise have a
15-minute response SLA.

## Security
All data is encrypted at rest with AES-256 and in transit with TLS 1.3.
SOC 2 Type II reports are available under NDA. SSO via SAML is included
on Pro and Enterprise.
""")
    return p


MAKERS = {"sales_data.csv": make_sales, "churn_data.csv": make_churn,
          "houses.csv": make_houses, "acme_faq.md": make_faq}


def ensure(filename: str) -> Path:
    path = HERE / filename
    if not path.exists():
        MAKERS[filename]()
    return path


if __name__ == "__main__":
    for name in MAKERS:
        print(f"generated {ensure(name)}")
