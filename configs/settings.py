from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# To support locally defined environment variables
load_dotenv()

class Settings(BaseSettings):
    is_env: str = "dev"
    app_name: str = ""
    app_instructions: str = ""
    app_version: str = "0.0.0"
    app_host: str = "localhost"
    app_port: int = 4200
    app_log_level: str = "info"
    app_transport: str = "stdio"
    app_path: str = ""
    app_message_path: str = ""
    db_host: str = "localhost"
    db_port: int = 1433
    db_name: str = ""
    db_uid: str = "sa"
    db_pwd: str = ""
    trust_server_certificate: str = "yes"
    encrypt: str = "no"