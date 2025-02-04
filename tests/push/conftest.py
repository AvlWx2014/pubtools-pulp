import datetime
import pytest

from more_executors.futures import f_return

from pubtools.pulplib import (
    Client,
    FileRepository,
    YumRepository,
    Task,
)

from pubtools._pulp.tasks.push import Push
from pubtools._pulp.services.fakepulp import PersistentFake


class FakePush(Push):
    def __init__(self, controller, *args, **kwargs):
        super(FakePush, self).__init__(*args, **kwargs)
        self.controller = controller

    @classmethod
    def cdn_published_value(cls):
        return datetime.datetime(2021, 12, 10, 9, 59)

    @property
    def pulp_client(self):
        # Super should give a Pulp client
        assert isinstance(super(FakePush, self).pulp_client, Client)

        # But we'll substitute our own
        return self.controller.client


class NoCopyPush(FakePush):
    @property
    def pulp_client(self):
        return NoCopyClient(super(NoCopyPush, self).pulp_client)


class NoCopyClient(object):
    """A pulplib.Client wrapper which stubs out any attempts to copy with a no-op.

    Simulates the case where a pulp copy request creates a successful
    task but content doesn't end up in target repo.
    """

    def __init__(self, delegate):
        self.search_content = delegate.search_content
        self.get_repository = delegate.get_repository

    def copy_content(self, *_args, **_kwargs):
        return f_return([Task(id="no-copy-123", completed=True, succeeded=True)])


@pytest.fixture
def fake_state_path(tmpdir):
    """Yields path to a temporary state file used by PersistentFake during each test."""
    return str(tmpdir.join("fake-pulp-state.yaml"))


@pytest.fixture
def fake_controller(fake_state_path):
    """Yields a pulplib FakeController which has been pre-populated with
    repos used by staged-mixed.
    """
    fake = PersistentFake(state_path=fake_state_path)
    fake.load_initial()
    controller = fake.ctrl

    # Add the repositories which are referenced from the staging area.
    controller.insert_repository(FileRepository(id="iso-dest1"))
    controller.insert_repository(FileRepository(id="iso-dest2"))
    controller.insert_repository(YumRepository(id="dest1"))
    controller.insert_repository(YumRepository(id="dest2"))

    yield controller


@pytest.fixture
def fake_push(fake_controller):
    """Yields an instance of a Push task which is connected to fake_controller."""
    yield FakePush(fake_controller)


@pytest.fixture
def fake_nocopy_push(fake_controller):
    """Yields an instance of a Push task which is connected to fake_controller and
    a client configured such that content copies won't work."""
    yield NoCopyPush(fake_controller)
