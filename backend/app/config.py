from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "leipal"
    postgres_user: str = "leipal"
    postgres_password: str = "changeme"
    database_url: str = "postgresql+psycopg://leipal:changeme@localhost:5432/leipal"
    data_dir: Path = Path("./data")

    model_config = {"env_file": "../.env", "extra": "ignore"}


settings = Settings()
