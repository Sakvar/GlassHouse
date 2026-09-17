import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from glasshouse.live.config import Settings
from glasshouse.live.i18n import editorial_options, episode_view
from glasshouse.live.narrator import OpenRouterNarrator
from glasshouse.live.schemas import Episode
from glasshouse.simulation.engine import SimulationEngine


def episode():
    engine = SimulationEngine()
    engine.tick()
    return episode_view(engine, 'en')


class FakeClient:
    def __init__(self, copy=None, error=None):
        self.copy = copy
        self.error = error
        self.chat = SimpleNamespace(completions=self)
        self.calls = []
        self.options = None

    def factory(self, **options):
        self.options = options
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(
            model='provider/fallback',
            usage=SimpleNamespace(model_dump=lambda: {
                'prompt_tokens': 50, 'completion_tokens': 40, 'cost': 0.0004}),
            choices=[SimpleNamespace(finish_reason='stop', message=SimpleNamespace(
                refusal=None, content=json.dumps(self.copy)))],
        )


def enabled():
    return Settings(llm_enabled=True, api_key='never-log-this-key', narrator_model='provider/main',
                    narrator_fallbacks=('provider/fallback',), site_url='https://example.com')


def test_schema_normalization_does_not_corrupt_episode_types():
    e = episode()
    restored = Episode.model_validate(e.model_dump())
    assert restored.tick == 1 and restored.locale == 'en'
    assert isinstance(restored.participants, tuple)


def test_openrouter_url_headers_strict_schema_fallback_and_public_context(caplog):
    e = episode()
    options = editorial_options(e)
    fake = FakeClient({k: values[-1] for k, values in options.items()})
    result, audit = OpenRouterNarrator(enabled(), fake.factory).narrate(e, 'reveal_secret')
    assert result.narrated and result.headline == options['headline'][-1]
    assert fake.options['base_url'] == 'https://openrouter.ai/api/v1'
    assert fake.options['default_headers'] == {
        'HTTP-Referer': 'https://example.com', 'X-OpenRouter-Title': 'GlassHouse Live'}
    assert fake.options['max_retries'] == 0 and fake.options['timeout'] == 15
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call['extra_body'] == {'models': ['provider/main', 'provider/fallback'],
                                 'provider': {'require_parameters': True}}
    schema = call['response_format']['json_schema']
    assert schema['strict'] is True
    assert schema['schema']['additionalProperties'] is False
    assert set(schema['schema']['required']) == set(options)
    assert call['max_tokens'] == 600
    context = json.loads(call['messages'][1]['content'])
    assert set(context) == {'participants', 'category', 'outcome', 'relationship_changes',
                            'locale', 'previous_public_recap', 'approved_copy'}
    assert audit['model_used'] == 'provider/fallback' and audit['cost'] == 0.0004
    assert audit['prompt_tokens'] == 50
    assert 'never-log-this-key' not in caplog.text


@pytest.mark.parametrize('settings', [Settings(), replace(enabled(), llm_enabled=False),
                                      replace(enabled(), api_key=''),
                                      replace(enabled(), llm_max_calls=0)])
def test_disabled_narrator_does_not_construct_client(settings):
    def forbidden(**kwargs):
        pytest.fail('No client should be constructed')
    e = episode()
    result, audit = OpenRouterNarrator(settings, forbidden).narrate(e, 'reveal_secret')
    assert result == e and audit['status'] == 'disabled'


@pytest.mark.parametrize('copy', [None, {'headline': 'bad'}, {
    'headline': 'Invented fact', 'what_happened': 'An invented scene happened.',
    'why_it_matters': 'Because the model decided.', 'teaser': 'More invented facts.'}])
def test_invalid_or_unapproved_narration_falls_back(copy):
    e = episode()
    fake = FakeClient(copy)
    result, audit = OpenRouterNarrator(enabled(), fake.factory).narrate(e, 'reveal_secret')
    assert result == e and audit['status'] == 'fallback'
    assert audit['error_type']


def test_provider_failure_is_safe_and_deterministic(caplog):
    caplog.set_level('INFO')
    e = episode()
    fake = FakeClient(error=TimeoutError('secret provider prompt and never-log-this-key'))
    result, audit = OpenRouterNarrator(enabled(), fake.factory).narrate(e, 'reveal_secret')
    assert result == e and audit['status'] == 'fallback'
    assert audit['error_type'] == 'TimeoutError'
    assert 'secret provider prompt' not in caplog.text
    assert 'never-log-this-key' not in caplog.text
    assert 'TimeoutError' in caplog.text


def test_rest_tick_does_not_call_provider():
    e = episode().model_copy(update={'outcome': 'rest'})
    fake = FakeClient()
    result, audit = OpenRouterNarrator(enabled(), fake.factory).narrate(e, 'conversation')
    assert result == e and audit['status'] == 'empty_tick' and not fake.calls


def test_real_network_is_blocked():
    import socket
    with socket.socket() as connection, pytest.raises(AssertionError, match='Real network'):
        connection.connect(('127.0.0.1', 443))
