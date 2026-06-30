import json
import os

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def config_path():
    return os.path.join(REPO_ROOT, "config.json")


@pytest.fixture
def config(config_path):
    with open(config_path, "r") as f:
        return json.load(f)


@pytest.fixture
def dockerfile_path():
    return os.path.join(REPO_ROOT, "Dockerfile")


@pytest.fixture
def dockerfile_content(dockerfile_path):
    with open(dockerfile_path, "r") as f:
        return f.read()


@pytest.fixture
def dockerfile_lines(dockerfile_content):
    return [line.strip() for line in dockerfile_content.splitlines() if line.strip()]
