from html.parser import HTMLParser
from io import StringIO


class StripHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, d: str) -> None:
        self.text.write(d)

    def get_data(self) -> str:
        return self.text.getvalue()


def strip_tags(html_string: str) -> str:
    """
    Strip HTML tags from string

    :param html_string: String with HTML tags
    :return: html_string with HTML tags removed
    """
    s = StripHTML()
    s.feed(html_string)
    return s.get_data()
