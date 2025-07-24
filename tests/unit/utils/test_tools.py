from src.krm3.utils.tools import uniq, parse_emails

def test_uniq():
    assert list(uniq([1, 2, 3])) == [1, 2, 3]
    assert list(uniq([1, 1, 1])) == [1]

def test_parse_emails():
    assert parse_emails('a@b.com,c@d.com') == [('a', 'a@b.com'), ('c', 'c@d.com')]
