from core.train_manager import TrainManger

from utils.constants import OPEN_DATA_API_BASE, OPEN_DATA_API_KEY

from typing import Any
from utils.constants import USER_AGENT, DEFAULT_TIMEOUT
import httpx
async def make_train_request(url: str, params: dict | None) -> dict[str, Any] | None:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    async with httpx.AsyncClient() as client:
        try:
            respose = await client.get(
                url=url,
                headers=headers,
                params=params,
                timeout=DEFAULT_TIMEOUT,
            )
            respose.raise_for_status()
            return respose.json()
        except Exception:
            return None


@TrainManger.get_mcp().tool()
async def get_train_code(train_name: str) -> str:
    url = f"{OPEN_DATA_API_BASE}/getVhcleKndList"
    params = {
        "serviceKey": OPEN_DATA_API_KEY,
        "_type": "json",
    }
    data = await make_train_request(url, params)
    items = data["response"]["body"]["items"]
    item_list = [item for item in items if item.vehiclekndnm == train_name]
    return "\n---\n".join(item_list)
    