"""Where things live on disk. Set DT_DATA to move the data folder (the tests do)."""
import json
import os

SOFTWARE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data(*parts):
    """A path under the data folder (sessions, characters, settings). Made on demand."""
    root = os.environ.get("DT_DATA") or os.path.join(SOFTWARE, "data")
    path = os.path.join(root, *parts)
    os.makedirs(os.path.dirname(path) if os.path.splitext(path)[1] else path, exist_ok=True)
    return path


def write_json(path, value, **how):
    """Write a JSON file so that a power cut never leaves half of one: the new
    file is written beside the old one, then swapped in."""
    text = json_text(value, **how)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def json_text(value, **how):
    """value as JSON that can be written to a UTF-8 file whatever is in it. A
    string holding half of a broken character cannot be written as it stands;
    then the whole text is written with escapes instead, which reads back as
    exactly the same value. So what is in memory and what is on disk never differ."""
    text = json.dumps(value, **how)
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        text = json.dumps(value, **dict(how, ensure_ascii=True))
    return text


def content_db():
    return os.environ.get("DT_CONTENT_DB") or os.path.join(SOFTWARE, "content.db")


def content_dir():
    return os.environ.get("DT_CONTENT") or os.path.join(SOFTWARE, "content")
