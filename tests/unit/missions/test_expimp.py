import json

from testutils.factories import (
    DocumentTypeFactory,
    ExpenseCategoryFactory,
    ExpenseFactory,
    PaymentCategoryFactory,
)

import pytest
import os
from krm3.missions.impexp.imp import MissionImporter
import zipfile
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile


def prepare():
    from krm3.missions.impexp.export import MissionExporter
    from krm3.missions.impexp.imp import MissionImporter
    from krm3.core.models import Expense, Mission

    assert Mission.objects.count() == 0

    original_mission = ExpenseFactory().mission
    expense = ExpenseFactory(mission=original_mission)

    payment_type = PaymentCategoryFactory(parent=expense.payment_type)
    category = ExpenseCategoryFactory(parent=expense.category)
    document_type = DocumentTypeFactory()
    ExpenseFactory(
        mission=original_mission,
        payment_type=payment_type,
        category=category,
        document_type=document_type,
    )
    assert Mission.objects.count() == 1
    assert Expense.objects.count() == 3

    pathname = MissionExporter(Mission.objects.all()).export()
    data = MissionImporter.get_data(pathname)

    assert len(data['clients']) == 1
    assert len(data['countries']) == 1
    assert len(data['projects']) == 1
    assert len(data['cities']) == 1
    assert len(data['categories']) == 3
    assert len(data['payment_types']) == 3
    assert len(data['missions']) == 1
    assert len(data['expenses']) == 3

    data_str = json.dumps(data)
    assert data_str.count('EXISTS') == 18
    assert data_str.count('ADD') == 0
    assert data_str.count('AMEND') == 0

    return data, pathname


def test_mission_full_expimp(db):
    from krm3.core.models import City, Country, Project, Resource
    from krm3.currencies.models import Currency
    from krm3.core.models import Expense, Mission

    data, pathname = prepare()
    # check it is json parseable
    json.dumps(data)

    Expense.objects.all().delete()
    Mission.objects.all().delete()
    Resource.objects.all().delete()
    City.objects.all().delete()
    Country.objects.all().delete()
    Project.objects.all().delete()
    Currency.objects.all().delete()

    assert Mission.objects.count() == 0
    assert Expense.objects.count() == 0
    assert City.objects.count() == 0
    assert Country.objects.count() == 0
    assert Project.objects.count() == 0
    assert Currency.objects.count() == 0

    data = MissionImporter.get_data(pathname)

    data['clients'].values()


@pytest.fixture
def valid_mission_zip():
    """Create a valid mission ZIP file in memory."""
    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add required directory
        zip_file.writestr('images/', '')

        # Add required data.json file
        data_json = {
            "missions": [
                {"id": 1, "name": "Test Mission", "description": "A test mission"}
            ]
        }
        import json

        zip_file.writestr('data.json', json.dumps(data_json, indent=2))

        # Add some sample images
        zip_file.writestr('images/image1.jpg', b'fake_image_data_1')
        zip_file.writestr('images/image2.jpg', b'fake_image_data_2')

    zip_buffer.seek(0)
    return zip_buffer


@pytest.fixture
def invalid_zip_missing_data():
    """Create an invalid ZIP file missing data.json."""
    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Only add images directory, missing data.json
        zip_file.writestr('images/', '')
        zip_file.writestr('images/image1.jpg', b'fake_image_data')

    zip_buffer.seek(0)
    return zip_buffer


@pytest.fixture
def invalid_zip_missing_images():
    """Create an invalid ZIP file missing images directory."""
    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Only add data.json, missing images directory
        zip_file.writestr('data.json', '{"missions": []}')

    zip_buffer.seek(0)
    return zip_buffer


@pytest.fixture
def non_zip_file():
    """Create a non-ZIP file for testing."""
    buffer = BytesIO()
    buffer.write(b'This is not a ZIP file content')
    buffer.seek(0)
    return buffer


@pytest.fixture
def create_in_memory_uploaded_file():
    """Factory fixture to create InMemoryUploadedFile instances."""

    def _create_file(
        content_buffer, filename='test.zip', content_type='application/zip'
    ):
        return InMemoryUploadedFile(
            file=content_buffer,
            field_name='file',
            name=filename,
            content_type=content_type,
            size=len(content_buffer.getvalue()),
            charset=None,
        )

    return _create_file


class TestMissionImporterStore:
    """Test cases for the store method."""

    def test_store_creates_file_with_correct_content(
        self, valid_mission_zip, create_in_memory_uploaded_file
    ):
        """Test that store creates a file with the correct content."""
        uploaded_file = create_in_memory_uploaded_file(valid_mission_zip)
        importer = MissionImporter(uploaded_file)

        pathname = importer.store()

        try:
            # Verify the file was created
            assert os.path.exists(pathname)

            # Verify the file has the correct suffix
            assert pathname.endswith('.zip')

            # Verify the content is correct by comparing sizes first
            original_size = len(valid_mission_zip.getvalue())
            assert os.path.getsize(pathname) == original_size

            # Verify it's a valid ZIP file
            assert zipfile.is_zipfile(pathname)

            # Verify ZIP content
            with zipfile.ZipFile(pathname, 'r') as zip_file:
                files = zip_file.namelist()
                assert 'images/' in files
                assert 'data.json' in files

        finally:
            # Clean up the temporary file
            if os.path.exists(pathname):
                os.unlink(pathname)

    def test_store_returns_valid_pathname(
        self, valid_mission_zip, create_in_memory_uploaded_file
    ):
        """Test that store returns a valid pathname."""
        uploaded_file = create_in_memory_uploaded_file(valid_mission_zip)
        importer = MissionImporter(uploaded_file)

        pathname = importer.store()

        try:
            # Verify pathname is a string
            assert isinstance(pathname, str)

            # Verify pathname is not empty
            assert pathname

            # Verify the file exists at the returned path
            assert os.path.exists(pathname)

            # Verify it's in a temp directory
            assert 'tmp' in pathname.lower() or 'temp' in pathname.lower()

        finally:
            # Clean up
            if os.path.exists(pathname):
                os.unlink(pathname)

    def test_store_file_can_be_read_after_creation(
        self, valid_mission_zip, create_in_memory_uploaded_file
    ):
        """Test that the stored file can be read and processed."""
        uploaded_file = create_in_memory_uploaded_file(valid_mission_zip)
        importer = MissionImporter(uploaded_file)

        pathname = importer.store()

        try:
            # Verify we can read the file as a ZIP
            with zipfile.ZipFile(pathname, 'r') as zip_file:
                # Read data.json content
                data_content = zip_file.read('data.json')
                assert b'missions' in data_content

                # Verify images directory exists
                assert any(name.startswith('images/') for name in zip_file.namelist())

        finally:
            if os.path.exists(pathname):
                os.unlink(pathname)


class TestMissionImporterIntegration:
    """Integration tests for both methods together."""

    def test_validate_then_store(
        self, valid_mission_zip, create_in_memory_uploaded_file
    ):
        """Test that validate and store can be called sequentially."""
        uploaded_file = create_in_memory_uploaded_file(valid_mission_zip)
        importer = MissionImporter(uploaded_file)

        # First validate
        importer.validate()

        # Then store
        pathname = importer.store()

        try:
            # Verify both operations worked
            assert os.path.exists(pathname)
            assert zipfile.is_zipfile(pathname)

            # Verify content is complete
            with zipfile.ZipFile(pathname, 'r') as zip_file:
                files = set(zip_file.namelist())
                assert 'images/' in files
                assert 'data.json' in files

        finally:
            if os.path.exists(pathname):
                os.unlink(pathname)

    def test_store_then_validate_different_instance(
        self, valid_mission_zip, create_in_memory_uploaded_file
    ):
        """Test storing file and then validating with a new instance using the stored file."""
        uploaded_file = create_in_memory_uploaded_file(valid_mission_zip)
        importer = MissionImporter(uploaded_file)

        # Store the file
        pathname = importer.store()

        try:
            # Create new InMemoryUploadedFile from stored file
            with open(pathname, 'rb') as f:
                new_buffer = BytesIO(f.read())

            new_uploaded_file = create_in_memory_uploaded_file(new_buffer)
            new_importer = MissionImporter(new_uploaded_file)

            # Validate with new instance - should work
            new_importer.validate()

        finally:
            if os.path.exists(pathname):
                os.unlink(pathname)
