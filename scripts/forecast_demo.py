"""Print a DockTech forecast for a demo route."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml.service import ForecastService


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--route", default="NEWCASTLE_PARADIP_THERMAL")
    p.add_argument("--vessel", default="PANAMAX")
    p.add_argument("--unit", default="USD_PER_MT")
    p.add_argument("--horizon", type=int, choices=[7, 30, 90], default=30)
    args = p.parse_args()

    result = ForecastService().forecast_dict(args.route, args.vessel, args.unit, args.horizon)
    print(f"Model: {result['model_version']}")
    print(f"Route: {result['route_id']} | Vessel: {result['vessel_class_id']} | Unit: {result['freight_unit']}")
    print(f"Horizon: {result['horizon']} days")
    print("date,central,lower,upper")
    for point in result["points"]:
        print(f"{point['date']},{point['central']:.2f},{point['lower']:.2f},{point['upper']:.2f}")


if __name__ == "__main__":
    main()
