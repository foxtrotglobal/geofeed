# Adding a New Provider

## 1. Create the provider file

```python title="providers/myplatform.py"
"""MyPlatform provider."""
from datetime import datetime
import httpx
import config
from geo import reverse_geocode
from models import GeoPost, SearchParams
from providers.base import BaseProvider

class MyPlatformProvider(BaseProvider):
    name = "myplatform"
    color = "#FF6600"          # Unique hex color for map markers

    def __init__(self):
        self.api_key = config.get("myplatform", "api_key")

    def is_configured(self) -> bool:
        return bool(self.api_key)  # or return True if no key needed

    async def search(self, params: SearchParams) -> list[GeoPost]:
        place_name = await reverse_geocode(params.latitude, params.longitude)
        # ... call the API ...
        posts = []
        for item in api_results:
            posts.append(GeoPost(
                platform="myplatform",
                post_id=item["id"],
                url=item["url"],
                text=item["text"][:200],
                author=item["username"],
                latitude=params.latitude,
                longitude=params.longitude,
                location_name=place_name,
            ))
        return posts
```

## 2. Register in server.py and main.py

```python
from providers.myplatform import MyPlatformProvider

ALL_PROVIDERS = {
    ...
    "myplatform": MyPlatformProvider,
}
```

## 3. Add to config.yaml.example

```yaml
myplatform:
  api_key: ""    # Get from platform.example.com/api
```

## 4. Add the map UI checkbox

In `templates/map.html`, add to the platforms div:

```html
<label><input type="checkbox" value="myplatform" checked /> MyPlatform</label>
```

And add the color to the `COLORS` object:

```js
myplatform: '#FF6600',
```

## 5. Write tests

```python title="tests/test_providers.py"
class TestMyPlatformProvider:
    @pytest.mark.asyncio
    async def test_search_returns_posts(self):
        from providers.myplatform import MyPlatformProvider
        api_response = {"items": [{"id": "1", "text": "test", "url": "..."}]}
        mock_client = _mock_async_client(_mock_http_response(api_response))
        with patch("providers.myplatform.config") as mock_config, \
             patch("providers.myplatform.httpx.AsyncClient", return_value=mock_client):
            mock_config.get.return_value = "test_key"
            posts = await MyPlatformProvider().search(PARAMS)
        assert len(posts) == 1
        assert posts[0].platform == "myplatform"
```
