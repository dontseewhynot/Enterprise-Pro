import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import json
import os

data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "city_centre_footfall.csv")

df = pd.read_csv(data_path)
df = df.dropna(how="all")
df = df.dropna(subset=["Total Footfall"])
df = df[df["Interval"] == "daily"]
df = df[df["Total Footfall"] < 500000]
df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
df = df.dropna(subset=["Date"])

df["day_of_week"] = df["Date"].dt.dayofweek
df["month"] = df["Date"].dt.month
df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
df["is_event"] = (df["Event took place"] == "YES").astype(int)

X = df[["day_of_week", "month", "is_weekend", "is_event"]]
y = df["Total Footfall"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print("MAE:", round(mae, 2))
print("R2:", round(r2, 2))


def predict_footfall(day_of_week, month, is_event):
    is_weekend = 1 if day_of_week >= 5 else 0
    row = pd.DataFrame([{
        "day_of_week": day_of_week,
        "month": month,
        "is_weekend": is_weekend,
        "is_event": is_event
    }])
    result = model.predict(row)[0]
    return round(float(result))


def get_metrics():
    return {
        "mae": round(mae, 2),
        "r2_score": round(r2, 2),
        "training_samples": len(X_train),
        "test_samples": len(X_test)
    }


def get_weekly_predictions(month=6, is_event=0):
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    output = []
    for i in range(7):
        predicted = predict_footfall(i, month, is_event)
        output.append({"day": days[i], "predicted_footfall": predicted})
    return output


if __name__ == "__main__":
    print(json.dumps(get_metrics(), indent=2))
    print(json.dumps(get_weekly_predictions(month=6, is_event=1), indent=2))

