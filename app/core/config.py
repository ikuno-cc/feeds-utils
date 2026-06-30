from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Feed Utils"
    app_version: str = "0.1.0"
    debug: bool = False

    max_input_length: int = 1_000_000
    max_output_length: int = 1_000_000

    strip_scripts: bool = True
    strip_styles: bool = True
    extract_article: bool = True
    fix_encoding: bool = True
    normalize_unicode: bool = True
    remove_emojis: bool = False
    remove_extra_whitespace: bool = True

    model_config = {"env_file": ".env", "env_prefix": "FEEDUTILS_", "extra": "ignore"}


settings = Settings()
