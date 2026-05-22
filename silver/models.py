from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime

class Inspection(BaseModel):
    # Add validation aliases on fields with different names in the source data.
    model_config = ConfigDict(str_strip_whitespace=True, validate_by_alias=True, validate_by_name=True)

    socrata_id: str = Field(validation_alias=':id')
    inspection_type: str | None = Field(default=None)
    borough: str | None = Field(default=None)
    zip_code: str | None = Field(default=None)
    inspection_date: datetime | None = Field(default=None)
    result: str | None = Field(default=None)
    approved_date: datetime | None = Field(default=None)
    latitude: float | None = Field(default=None)
    longitude: float | None = Field(default=None)
    nta: str | None = Field(default=None)
    community_board: str | None = Field(default=None)
    created_at: datetime | None = Field(validation_alias=':created_at')
    updated_at: datetime | None = Field(validation_alias=':updated_at')

    @field_validator('zip_code', mode='before')
    @classmethod
    def validate_zip_code(cls, value):
        if value is None:
            return None
        if str(value).strip() == '0':
            return None
        return value

    @field_validator('latitude', 'longitude', mode='before')
    @classmethod
    def handle_zero_coordinates(cls, value):
        if value is None:
            return None
        try:
            f = float(value)
            if abs(f) < 1e-10:
                return None
            return f
        except (ValueError, TypeError):
            return None