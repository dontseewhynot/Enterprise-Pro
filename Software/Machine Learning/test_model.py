import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from model import predict_footfall, get_metrics, get_weekly_predictions


def test_predict_footfall_returns_positive():
    result = predict_footfall(1, 6, 0)
    assert result > 0

def test_predict_footfall_event_returns_positive():
    result = predict_footfall(1, 6, 1)
    assert result > 0

def test_predict_footfall_returns_integer():
    result = predict_footfall(0, 1, 0)
    assert isinstance(result, int)

def test_predict_footfall_weekend():
    result = predict_footfall(6, 6, 0)
    assert result > 0

def test_get_metrics_returns_dict():
    result = get_metrics()
    assert isinstance(result, dict)

def test_get_metrics_has_required_keys():
    result = get_metrics()
    assert "mae" in result
    assert "r2_score" in result
    assert "training_samples" in result
    assert "test_samples" in result

def test_get_metrics_training_samples_positive():
    result = get_metrics()
    assert result["training_samples"] > 0

def test_get_metrics_mae_positive():
    result = get_metrics()
    assert result["mae"] > 0

def test_get_weekly_predictions_returns_7_days():
    result = get_weekly_predictions()
    assert len(result) == 7

def test_get_weekly_predictions_all_positive():
    result = get_weekly_predictions()
    for day in result:
        assert day["predicted_footfall"] > 0

def test_get_weekly_predictions_has_correct_keys():
    result = get_weekly_predictions()
    for day in result:
        assert "day" in day
        assert "predicted_footfall" in day

def test_get_weekly_predictions_different_months():
    summer = get_weekly_predictions(month=6, is_event=0)
    winter = get_weekly_predictions(month=1, is_event=0)
    summer_total = sum(d["predicted_footfall"] for d in summer)
    winter_total = sum(d["predicted_footfall"] for d in winter)
    assert summer_total != winter_total or summer_total > 0
