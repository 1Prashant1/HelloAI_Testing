from typing import Dict, Any, List

class MenuTools:
    def __init__(self, store):
        self.store = store

    def list_categories(self) -> List[str]:
        return self.store.categories()

    def get_category(self, category: str) -> Dict[str, Any]:
        return self.store.get(category)

    def search_items(self, query: str) -> List[Dict[str, Any]]:
        q = (query or "").strip().lower()
        if not q:
            return []
        out = []
        for cat in self.store.categories():
            cat_data = self.store.get(cat)
            for it in cat_data.get("items", []):
                name = (it.get("name") or "").strip()
                if name and q in name.lower():
                    out.append({"category": cat, "name": name})
        return out

    def build_digest(self) -> str:
        lines = []
        for cat in self.store.categories():
            lines.append(f"- {cat}:")
            data = self.store.get(cat)
            names = [i.get("name", "").strip() for i in data.get("items", []) if i.get("name")]
            if names:
                lines.append("  " + ", ".join(names))
        return "\n".join(lines)
