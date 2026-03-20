import os
from pathlib import Path

class PathManager:
    """
    Centralized path manager for the IBKR Portfolio Analyzer.
    Automatically resolves absolute paths safely from any working directory.
    """

    BASE_DIR: Path = Path(__file__).resolve().parent.parent

    ASSETS_DIR: Path = BASE_DIR / "assets"
    CORE_DIR: Path = BASE_DIR / "core"
    PAGES_DIR: Path = BASE_DIR / "pages"
    WORKERS_DIR: Path = BASE_DIR / "workers"
    TESTS_DIR: Path = BASE_DIR / "tests"

    CONFIG_FILE: Path = Path(os.getenv("APP_CONFIG_FILE", BASE_DIR / "config.json"))
    PROMPTS_FILE: Path = Path(os.getenv("APP_PROMPTS_FILE", BASE_DIR / "prompts.json"))
    STYLE_FILE: Path = Path(os.getenv("APP_STYLE_FILE", ASSETS_DIR / "style.qss"))

    @classmethod
    def get_asset(cls, filename: str) -> Path:
        """
        Returns the absolute path for a file inside the assets directory.
        """
        return cls.ASSETS_DIR / filename