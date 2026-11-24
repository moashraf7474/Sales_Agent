"""Generates a sample sales file (sample_sales.csv) so you can try the agent."""

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

products = {
    "Sport T-Shirt": 350, "Gym Shorts": 300, "Hoodie": 750, "Full Tracksuit": 1100,
    "Sport Socks": 80, "Gym Bag": 450, "Training Gloves": 200, "Water Bottle": 120,
    "Cap": 180, "Leggings": 400, "Sport Jacket": 900, "Backpack": 650,
}
# The first products are the most popular, the last ones the least (so some products are stagnant)
weights = np.linspace(1.0, 0.05, len(products))
weights /= weights.sum()

cities = ["Cairo", "Giza", "Alexandria", "Mansoura", "Assiut"]
n = 1500
dates = pd.to_datetime("2026-06-01") + pd.to_timedelta(rng.integers(0, 150, n), unit="D")
names = rng.choice(list(products), n, p=weights)

df = pd.DataFrame(
    {
        "date": dates,
        "product": names,
        "city": rng.choice(cities, n, p=[0.4, 0.2, 0.2, 0.1, 0.1]),
        "quantity": rng.integers(1, 5, n),
    }
)
df["unit_price"] = df["product"].map(products)
df["total"] = df["quantity"] * df["unit_price"]
df = df.sort_values("date").reset_index(drop=True)

df.to_csv("sample_sales.csv", index=False)
print(f"Created sample_sales.csv ({len(df)} rows)")
