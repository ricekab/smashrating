import logging

from pydantic import Field, PostgresDsn
import pydantic_settings

_l = logging.getLogger(__name__)


class Settings(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(
        env_prefix="SMASHRATING_", env_file=".env", env_file_encoding="utf-8"
    )

    # DATABASE
    DB_HOST: str = Field(default="localhost", description="Database host address")
    DB_PORT: int = Field(default=54329, description="Database port number")
    DB_NAME: str = Field(default="ratingdb", description="Name of the database")
    DB_USER: str = Field(default="ratingdbo", description="Database user name")
    DB_PASSWORD: str = Field(
        default="ratingdbopw", description="Database user password"
    )

    TEST_DB_URI: PostgresDsn = Field(
        default=PostgresDsn(
            "postgresql+psycopg://ratingdbo:ratingdbopw@localhost:54329/ratingdbo"
        ),
        description="URI for the test database, used in testing",
    )

    @property
    def db_uri(self) -> str:
        """Connect String for SQLAlchemy Engine."""
        return (
            "postgresql+psycopg://"
            f"{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()
