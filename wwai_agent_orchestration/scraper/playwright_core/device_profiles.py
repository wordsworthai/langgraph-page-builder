from enum import Enum
from typing import Dict, Any


class DeviceType(str, Enum):
    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"


def get_profile(device_type: "DeviceType", *, dpr: float = 2.0) -> Dict[str, Any]:
    """
    Return a dict with keys: viewport, device_scale_factor, is_mobile, user_agent.
    """
    if device_type == DeviceType.DESKTOP:
        return {
            "viewport": {"width": 1440, "height": 900},
            "device_scale_factor": dpr,
            "is_mobile": False,
            "user_agent": None,
        }
    if device_type == DeviceType.MOBILE:
        return {
            "viewport": {"width": 375, "height": 667},
            "device_scale_factor": dpr,
            "is_mobile": True,
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
                          "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 "
                          "Mobile/15E148 Safari/604.1",
        }
    if device_type == DeviceType.TABLET:
        return {
            "viewport": {"width": 768, "height": 1024},
            "device_scale_factor": dpr,
            "is_mobile": True,
            "user_agent": "Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) "
                          "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 "
                          "Mobile/15E148 Safari/604.1",
        }
    # fallback to desktop
    return get_profile(DeviceType.DESKTOP, dpr=dpr)


