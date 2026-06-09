import json

from models.training.predict import load_model, predict
from serverless.ports import PORTS


def main():
    model = load_model()
    results = {}
    succeeded, failed = 0, 0

    for port_code in PORTS:
        try:
            results[port_code] = predict(model, port_code)
            succeeded += 1
        except Exception as e:
            results[port_code] = None
            failed += 1
            print(f"⚠️  {port_code} failed: {e}")

    output_path = "dashboard-v2/public/predictions.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"✅ {succeeded} ok, {failed} failed → {output_path}")


if __name__ == "__main__":
    main()
