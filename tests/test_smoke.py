from aikit import __version__
from aikit.embeddings import EmbeddingService
from aikit.model_client import ChatMessage, ModelClient


def test_version():
    assert isinstance(__version__, str)


def test_chat_message_immutable():
    m = ChatMessage(role="user", content="hi")
    assert m.role == "user"


def test_protocols_importable():
    assert ModelClient is not None
    assert EmbeddingService is not None
