from pydantic import BaseModel, Field, validator
from typing import Dict
class VehicleConfig(BaseModel):
    vehicle_mass: float = Field(gt=0)
    wing_area: float = Field(gt=0)
    cd0: float = Field(gt=0)
    induced_drag_k: float = Field(gt=0)
    nose_radius: float = Field(gt=0)
class AppConfig(BaseModel):
    vehicle: VehicleModel
class FederalConfigLoader(BaseSettings):
    """
    FAA/Federal-Compliant Config Loader.
    Automatically merges config.json with Environment Variables.
    """
    model_config = SettingsConfigDict(
        json_file='config.json', 
        json_file_encoding='utf-8',
        env_nested_delimiter='__'
    )    
    vehicle: VehicleModel
def get_validated_config():
    try:
        return FederalConfigLoader()
    except ValidationError as e:
        print(f"CRITICAL: CONFIGURATION VALIDATION FAILED: {e}")
        raise
class PlanetaryProfile(BaseModel):
    R_p: float = Field(gt=0)
    g0: float = Field(gt=0)
    rho0: float = Field(ge=0) # Can be 0 for space
    H: float = Field(gt=0)
def validate_configuration(config_data: Dict):
    """
    Parses and validates configuration maps.
    Raises ValueError for non-positive numbers or formatting errors.
    """
    validated = VehicleConfig(**config_data["Starship_Class"])
    return validated
