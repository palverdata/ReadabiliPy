from dataclasses import dataclass
from typing import Optional

@dataclass
class ReadableArticle:
    title: Optional[str] = None
    byline: Optional[str] = None
    dir: Optional[str] = None
    lang: Optional[str] = None
    content: Optional[str] = None
    text_content: Optional[str] = None
    length: Optional[int] = None
    excerpt: Optional[str] = None
    site_name: Optional[str] = None
    published_time: Optional[str] = None

    @staticmethod
    def from_json(json: dict) -> 'ReadableArticle':
        return ReadableArticle(
            title=json.get('title'),
            byline=json.get('byline'),
            dir=json.get('dir'),
            lang=json.get('lang'),
            content=json.get('content'),
            text_content=json.get('textContent'),
            length=json.get('length'),
            excerpt=json.get('excerpt'),
            site_name=json.get('siteName'),
            published_time=json.get('publishedTime')
        )
