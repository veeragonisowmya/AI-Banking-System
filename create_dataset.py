import pandas as pd
import random

data = []

for i in range(1000):

    amount = random.randint(500,100000)

    device = random.choice([
        "Known",
        "New"
    ])

    location = random.choice([
        "Home",
        "Different"
    ])

    time = random.choice([
        "Day",
        "Night"
    ])

    fraud_score = 0

    if amount > 50000:
        fraud_score += 1

    if device == "New":
        fraud_score += 1

    if location == "Different":
        fraud_score += 1

    if time == "Night":
        fraud_score += 1

    if fraud_score >= 3:
        fraud = 1
    else:
        fraud = 0

    data.append([
        amount,
        device,
        location,
        time,
        fraud
    ])

df = pd.DataFrame(
    data,
    columns=[
        "Amount",
        "Device",
        "Location",
        "Time",
        "Fraud"
    ]
)

df.to_csv("fraud_dataset.csv",index=False)

print("Dataset Created Successfully!")