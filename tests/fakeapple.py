"""A fake of Apple's endpoints so tests never touch the network."""

from datetime import datetime, timedelta, timezone

NOW = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)

APP = {
    "trackId": 1234567890,
    "trackName": "Sample Notes",
    "sellerName": "Sample Co",
    "primaryGenreName": "Productivity",
    "formattedPrice": "Free",
    "version": "3.1.0",
    "currentVersionReleaseDate": (NOW - timedelta(days=10)).isoformat().replace("+00:00", "Z"),
    "averageUserRating": 4.8,
    "userRatingCount": 120000,
    "trackViewUrl": "https://apps.apple.com/us/app/sample-notes/id1234567890",
}


def entry(i, rating, version, days_ago, title="Title", content="Body", votes=0):
    return {
        "id": {"label": str(1000 + i)},
        "im:rating": {"label": str(rating)},
        "im:version": {"label": version},
        "updated": {"label": (NOW - timedelta(days=days_ago)).isoformat()},
        "title": {"label": title},
        "content": {"label": content, "attributes": {"type": "text"}},
        "im:voteCount": {"label": str(votes)},
    }


def make_entries():
    out = []
    i = 0
    # older version 3.0.0: happy
    for k in range(15):
        out.append(entry(i, 5 if k % 5 else 4, "3.0.0", 40 + k)); i += 1
    # newer version 3.1.0: unhappy, crashes and subscription complaints
    complaints = [
        ("Crashes constantly", "The app crashes every time I open a note since the update."),
        ("Paywall", "They moved basic features behind a subscription. Total rip off."),
        ("Lost my notes", "Sync failed and I lost all my notes."),
    ]
    for k in range(45):
        t, c = complaints[k % 3]
        out.append(entry(i, 1 if k % 4 else 2, "3.1.0", k % 9, t, c, votes=k % 7)); i += 1
    for k in range(5):
        out.append(entry(i, 5, "3.1.0", 2, "Great", "Love it")); i += 1
    return out


class FakeApple:
    def __init__(self, app=None, entries=None, search_results=None):
        self.app = APP if app is None else app
        self.entries = make_entries() if entries is None else entries
        self.search_results = [self.app] if search_results is None else search_results
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        if "/lookup?" in url:
            return {"resultCount": 1 if self.app else 0, "results": [self.app] if self.app else []}
        if "/search?" in url:
            return {"results": self.search_results}
        if "/customerreviews/" in url:
            page = int(url.split("page=")[1].split("/")[0])
            chunk = self.entries[(page - 1) * 50 : page * 50]
            if not chunk:
                return {}
            # Apple's feed sometimes leads with an app-info entry with no rating
            lead = [{"im:name": {"label": "Sample Notes"}}] if page == 1 else []
            return {"feed": {"entry": lead + chunk}}
        raise AssertionError(url)
