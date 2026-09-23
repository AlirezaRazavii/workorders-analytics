# api contract tests: status codes, shapes and key figures

API_PREFIX = "/api"


def test_health(client):
    res = client.get(f"{API_PREFIX}/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_periods_sorted(client):
    res = client.get(f"{API_PREFIX}/periods")
    assert res.status_code == 200
    body = res.json()
    assert [p["date_id"] for p in body] == [140107, 140108, 140109]


def test_kpis_latest_month(client):
    res = client.get(f"{API_PREFIX}/kpis")
    assert res.status_code == 200
    body = res.json()
    assert body["date_id"] == 140109
    assert body["total_open"] == 1106
    assert body["mom_change"] == -104
    assert body["mom_change_pct"] == -8.6
    assert body["top_city"]["city_name"] == "شهر 5"
    assert body["top_category"]["label"] == "نیرورسانی"


def test_kpis_first_month_has_no_change(client):
    res = client.get(f"{API_PREFIX}/kpis?date_id=140107")
    body = res.json()
    assert body["total_open"] == 1559
    assert body["mom_change"] is None
    assert body["mom_change_pct"] is None


def test_kpis_unknown_date_returns_404(client):
    res = client.get(f"{API_PREFIX}/kpis?date_id=999999")
    assert res.status_code == 404


def test_trend(client):
    res = client.get(f"{API_PREFIX}/trend")
    body = res.json()
    assert [p["value"] for p in body] == [1559, 1210, 1106]


def test_by_category_mehr(client):
    res = client.get(f"{API_PREFIX}/by-category?date_id=140107")
    body = res.json()
    labels = [s["label"] for s in body]
    assert labels[0] == "نیرورسانی"
    assert body[0]["value"] == 673
    total_share = round(sum(s["share"] for s in body), 1)
    assert abs(total_share - 100.0) < 0.5


def test_by_city_top_is_city5_in_azar(client):
    res = client.get(f"{API_PREFIX}/by-city")
    body = res.json()
    assert body[0]["city_code"] == 7001
    assert body[0]["value"] == 164


def test_city_trend_unknown_city_returns_404(client):
    res = client.get(f"{API_PREFIX}/city-trend?city_code=99999")
    assert res.status_code == 404


def test_city_detail_sums_match_cell(client):
    # detail rows of city 9 in mehr must sum to its known total
    res = client.get(f"{API_PREFIX}/city-detail?city_code=2001&date_id=140107")
    body = res.json()
    assert len(body) == 7
    assert sum(r["total"] for r in body) == 220
    wire = next(r for r in body if r["category_name"] == "سیم به کابل")
    assert wire["total"] == 29


def test_matrix_shape(client):
    res = client.get(f"{API_PREFIX}/matrix?date_id=140107")
    body = res.json()
    assert len(body) == 16
    assert all(len(row["values"]) == 7 for row in body)
    total = sum(row["total"] for row in body)
    assert total == 1559


def test_city_status_totals(client):
    res = client.get(f"{API_PREFIX}/city-status?date_id=140107")
    body = res.json()
    assert sum(row["total"] for row in body) == 1559
    in_progress = sum(row["values"]["در دست اجرا"] for row in body)
    assert in_progress == 1446


def test_etl_status(client):
    res = client.get(f"{API_PREFIX}/etl-status")
    body = res.json()
    assert body["run_status"] == "success"
    assert body["rows_loaded"] == 1536