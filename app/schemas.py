# response models used by the api endpoints
from datetime import datetime

from pydantic import BaseModel


class Period(BaseModel):
    date_id: int
    jalali_year: int
    jalali_month: int
    year_label: str
    month_name: str


class CityValue(BaseModel):
    city_code: int
    city_name: str
    value: int


class LabelValue(BaseModel):
    label: str
    value: int


class Slice(BaseModel):
    label: str
    value: int
    share: float | None = None


class TrendPoint(BaseModel):
    date_id: int
    year_label: str
    month_name: str
    value: int


class Kpis(BaseModel):
    date_id: int
    year_label: str
    month_name: str
    total_open: int
    prev_total_open: int | None = None
    mom_change: int | None = None
    mom_change_pct: float | None = None
    active_cities: int
    top_category: LabelValue | None = None
    top_city: CityValue | None = None


class MatrixRow(BaseModel):
    city_code: int
    city_name: str
    values: dict[str, int]
    total: int


class EtlRun(BaseModel):
    run_id: int
    started_at: datetime
    finished_at: datetime | None = None
    run_status: str
    rows_extracted: int | None = None
    rows_loaded: int | None = None
    checks_total: int | None = None
    checks_failed: int | None = None
    
class DetailRow(BaseModel):
    category_order: int
    category_name: str
    values: dict[str, int]
    total: int