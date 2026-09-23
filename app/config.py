from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # values are read from the .env file in the project root
    model_config = SettingsConfigDict(env_file=".env")

    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_host: str = "localhost"
    postgres_port: str = "5432"
    db_name: str = "workorders_dwh"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.db_name}"
        )


settings = Settings()