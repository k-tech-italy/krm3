import pytest

from krm3.web.templatetags.nav_bar import nav_bar


def render_nav_bar(banner: dict | None) -> str:
    context = {'csrf_token': 'token'}
    if banner is not None:
        context['ENVIRONMENT_BANNER'] = banner
    return str(nav_bar(context, {'Report': '/be/report/'}, logout_url='/logout/'))


@pytest.mark.parametrize(
    ('banner', 'label', 'color'),
    [
        pytest.param(
            {'environment': 'local', 'show_banner': True, 'label': 'LOCAL', 'color': '#fed7aa'},
            'LOCAL',
            '#fed7aa',
            id='local',
        ),
        pytest.param(
            {'environment': 'int', 'show_banner': True, 'label': 'INT', 'color': '#86efac'},
            'INT',
            '#86efac',
            id='int',
        ),
    ],
)
def test_nav_bar_shows_environment_strip(banner, label, color):
    html = render_nav_bar(banner)
    assert 'data-environment-banner' in html
    assert label in html
    assert color in html
    # the strip must sit inside the fixed navbar, above the brand row
    nav = html.find('<nav')
    strip = html.find('data-environment-banner')
    brand = html.find('KRM³</span>')
    assert nav < strip < brand
    # the page content must be pushed below the taller navbar
    assert 'body { padding-top: 28px; }' in html


def test_nav_bar_hides_strip_on_production():
    banner = {'environment': 'production', 'show_banner': False, 'label': '', 'color': ''}
    html = render_nav_bar(banner)
    assert 'data-environment-banner' not in html
    assert 'padding-top' not in html


def test_nav_bar_without_banner_in_context():
    html = render_nav_bar(None)
    assert 'data-environment-banner' not in html
    assert 'padding-top' not in html
