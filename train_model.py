import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib

# STEP 1 : Load Dataset

df = pd.read_csv("fraud_dataset.csv")

print("Dataset Loaded Successfully\n")

print(df.head())

print("\nDataset Shape :", df.shape)

print("\nDataset Information")
print(df.info())

print("\nMissing Values")
print(df.isnull().sum())

# STEP 2 : Encode Categorical Columns

device_encoder = LabelEncoder()
location_encoder = LabelEncoder()
time_encoder = LabelEncoder()

df["Device"] = device_encoder.fit_transform(df["Device"])

df["Location"] = location_encoder.fit_transform(df["Location"])

df["Time"] = time_encoder.fit_transform(df["Time"])

# STEP 3 : Separate Features and Target

X = df[["Amount", "Device", "Location", "Time"]]

y = df["Fraud"]

print("\nFeatures")
print(X.head())

print("\nTarget")
print(y.head())

# STEP 4 : Split Dataset

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print("\nTraining Data :", len(X_train))

print("Testing Data :", len(X_test))

# STEP 5 : Train Model

model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)

model.fit(X_train, y_train)

print("\nModel Training Completed Successfully")

# -----------------------------------
# STEP 6 : Test Model
# -----------------------------------

y_pred = model.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)

print("\nModel Accuracy :", round(accuracy * 100, 2), "%")

print("\nClassification Report\n")

print(classification_report(y_test, y_pred))

# -----------------------------------
# STEP 7 : Save Model
# -----------------------------------

joblib.dump(model, "fraud_model.pkl")

joblib.dump(device_encoder, "device_encoder.pkl")

joblib.dump(location_encoder, "location_encoder.pkl")

joblib.dump(time_encoder, "time_encoder.pkl")

print("\nModel Saved Successfully")

print("fraud_model.pkl")

print("device_encoder.pkl")

print("location_encoder.pkl")

print("time_encoder.pkl")
