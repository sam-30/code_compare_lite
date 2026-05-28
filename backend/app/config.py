from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    output_dir: str = "/output"

settings = Settings()
