import os


def _local_value(name):
    try:
        import config_local  # type: ignore
    except ImportError:
        return None
    return getattr(config_local, name, None)


# 讯飞星火 API 配置
API_KEY = os.getenv("API_KEY") or _local_value("API_KEY") or "your_api_key_here"
API_SECRET = os.getenv("API_SECRET") or _local_value("API_SECRET") or "your_api_secret_here"
API_FLOW_ID = os.getenv("API_FLOW_ID") or _local_value("API_FLOW_ID") or "your_flow_id_here"
XUN_FEI_URL = os.getenv("XUN_FEI_URL") or _local_value("XUN_FEI_URL") or "your_xun_fei_url_here"

