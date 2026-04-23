from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    HUAWEI_CLIENT_ID: str = ""
    HUAWEI_CLIENT_SECRET: str = ""

    STRAVA_CLIENT_ID: str = ""
    STRAVA_CLIENT_SECRET: str = ""
    STRAVA_ACCESS_TOKEN: str = ""
    STRAVA_REFRESH_TOKEN: str = ""

    JEFIT_USER_ID: str = ""

    GEMINI_API_KEY: str = ""

    DATABASE_PATH: str = "./fitness.db"
    SECRET_KEY: str = "change-me"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
