import datetime
import json
import typing
from datetime import date

import pytest
from testutils.factories import ResourceFactory


@pytest.mark.parametrize(
    'vcard_text, should_be_valid, test_description',
    [
        pytest.param(None, True, 'None vcard_text', id='none'),
        pytest.param('', True, 'Empty vcard_text', id='empty'),
        pytest.param(
            'BEGIN:VCARD\nVERSION:3.0\nFN:John Doe\nN:Doe;John;;;\nTEL:+1234567890\nEMAIL:john@example.com\nEND:VCARD',
            True,
            'Valid vCard with Unix line endings',
            id='valid-unix',
        ),
        pytest.param(
            'BEGIN:VCARD\r\nVERSION:3.0\r\nFN:Jane Smith\r\nN:Smith;Jane;;;\r\nEND:VCARD\r\n',
            True,
            'Valid vCard with Windows line endings',
            id='valid-windows',
        ),
        pytest.param(
            (
                'BEGIN:VCARD\nVERSION:3.0\nFN:John Doe\nN:Doe;John;;;\n'
                'item1.TEL:+1234567890\nitem1.X-ABLabel:iPhone\nEND:VCARD'
            ),
            True,
            'Valid vCard with Apple extensions',
            id='valid-apple-extensions',
        ),
        pytest.param(
            'BEGIN:VCARD\nFN:John Doe\nEND:VCARD',
            True,
            'vCard without VERSION (lenient parsing)',
            id='no-version',
        ),
        pytest.param(
            'BEGIN:VCARD\nVERSION:3.0\nEND:VCARD',
            True,
            'vCard without FN/N (lenient parsing)',
            id='no-fn',
        ),
        pytest.param(
            'This is not a vCard',
            False,
            'Malformed vCard',
            id='malformed',
        ),
        pytest.param(
            'BEGIN:VCARD\nVERSION:3.0\nFN:Test\nN:Test;;;\nEND:VCAR',
            False,
            'Invalid vCard with incomplete END tag',
            id='incomplete-end',
        ),
    ],
)
def test_resource_vcard_validation(vcard_text, should_be_valid, test_description):
    """Test vCard validation for the Resource model using vobject.

    vobject is more lenient than strict RFC 2426 validation and supports:
    - vCard 2.1, 3.0, and 4.0 formats
    - Apple-specific extensions (item1.TEL, X-ABLabel, etc.)
    - Missing VERSION or FN/N fields (lenient mode)
    """
    from django.core.exceptions import ValidationError

    resource = ResourceFactory(vcard_text=vcard_text)

    if should_be_valid:
        # Should not raise ValidationError
        resource.clean()
    else:
        # Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            resource.clean()
        assert 'vcard_text' in exc_info.value.message_dict
