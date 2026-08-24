import json


def json_ld(data):
    """Serialize a dict to a string safe to embed directly inside a
    <script type="application/ld+json"> tag. json.dumps already produces
    valid, properly-escaped JSON; the only extra step needed for safe HTML
    embedding is guarding against a "</script>" substring (e.g. from a
    product description) breaking out of the surrounding tag."""
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
