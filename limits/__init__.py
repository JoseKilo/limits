from .config import DevConfig
from .limits import create_app


app = create_app(DevConfig)
