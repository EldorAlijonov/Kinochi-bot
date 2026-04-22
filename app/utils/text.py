from html import escape


def safe_html(value: object) -> str:
    return escape(str(value), quote=True)
