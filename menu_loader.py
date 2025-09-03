import os, json
from typing import Dict, Any, List

class MenuStore:
    """
    Loads all *.json files from the directory into a category map.
    Each file:
      { "category": "Burgers", "items": [ {"name": "Chicken Smash", ...}, ... ] }
    """
    def __init__(self, folder: str):
        self.folder = folder
        self._cache: Dict[str, Any] = {}
        self._load_all()

    def _load_all(self):
        if not os.path.isdir(self.folder):
            os.makedirs(self.folder, exist_ok=True)
        for fn in os.listdir(self.folder):
            if fn.lower().endswith(".json"):
                path = os.path.join(self.folder, fn)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        cat = data.get("category") or os.path.splitext(fn)[0].title()
                        self._cache[cat] = data
                except Exception:
                    pass
        if not self._cache:
            self._cache = {
                "Burgers": {"category": "Burgers", "items": [{"name": "Chicken Smash"}]},
                "Pizza": {"category": "Pizza", "items": [{"name": "Margherita"}]}
            }

    def snapshot(self) -> Dict[str, Any]:
        return self._cache

    def categories(self) -> List[str]:
        return sorted(self._cache.keys())

    def get(self, category: str) -> Dict[str, Any]:
        if category in self._cache:
            return self._cache[category]
        for k in self._cache:
            if k.lower() == (category or "").lower():
                return self._cache[k]
        return {"category": category, "items": []}

    def get_any_sample(self) -> Dict[str, Any]:
        for k in self.categories():
            d = self._cache[k]
            if d.get("items"):
                return {"category": k, "first_item": d["items"][0]}
        return {}
