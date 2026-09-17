from __future__ import annotations

import json
import logging
import time

from openai import OpenAI

from glasshouse.live.i18n import editorial_options
from glasshouse.live.schemas import NarratedRecap

logger = logging.getLogger(__name__)


class OpenRouterNarrator:
    """One bounded editorial call after resolution; never a simulation provider."""

    def __init__(self, settings, client_factory=OpenAI):
        self.settings = settings
        self.client_factory = client_factory

    def narrate(self, episode, category, previous=None):
        s = self.settings
        audit = dict(
            role='narrator', model_requested=s.narrator_model, model_used=None,
            status='disabled', prompt_tokens=None, completion_tokens=None, cost=None,
            latency_ms=0, error_type=None,
        )
        if not (s.llm_enabled and s.api_key and s.narrator_model and s.llm_max_calls):
            return episode, audit
        if episode.outcome == 'rest':
            audit['status'] = 'empty_tick'
            return episode, audit
        started = time.monotonic()
        try:
            options = editorial_options(episode)
            # Only resolved public facts and authored copy cross this boundary.
            context = {
                'participants': episode.participants, 'category': category,
                'outcome': episode.outcome, 'relationship_changes': episode.relationship_changes,
                'locale': episode.locale,
                'previous_public_recap': previous.what_happened if previous else None,
                'approved_copy': options,
            }
            content = json.dumps(context, ensure_ascii=False)
            if len(content) > s.llm_input_chars:
                raise ValueError('InputBudgetExceeded')
            schema = NarratedRecap.model_json_schema()
            for key, values in options.items():
                schema['properties'][key]['enum'] = values
            headers = {}
            if s.site_url:
                headers['HTTP-Referer'] = s.site_url
            if s.app_name:
                headers['X-OpenRouter-Title'] = s.app_name
            # Zero automatic HTTP retries: a strict one-call-per-tick cap. OpenRouter
            # performs model fallbacks within this single request.
            with self.client_factory(
                api_key=s.api_key, base_url='https://openrouter.ai/api/v1',
                default_headers=headers, timeout=s.llm_timeout, max_retries=0,
            ) as client:
                response = client.chat.completions.create(
                    model=s.narrator_model,
                    messages=[
                        {'role': 'system', 'content':
                         'Edit a safe AI reality recap in the given locale. Choose each field '
                         'verbatim from approved_copy. Prefer variety from the previous recap. '
                         'Never invent facts, dialogue, consent, private reasons or outcomes.'},
                        {'role': 'user', 'content': content},
                    ],
                    response_format={'type': 'json_schema', 'json_schema': {
                        'name': 'NarratedRecap', 'strict': True, 'schema': schema,
                    }},
                    extra_body={
                        'models': [s.narrator_model, *s.narrator_fallbacks],
                        'provider': {'require_parameters': True},
                    },
                    max_tokens=s.llm_max_tokens,
                )
            audit['model_used'] = response.model
            if response.usage:
                usage = response.usage.model_dump()
                for key in ('prompt_tokens', 'completion_tokens', 'cost'):
                    audit[key] = usage.get(key)
            message = response.choices[0].message
            if message.refusal or response.choices[0].finish_reason != 'stop':
                raise ValueError('IncompleteOrRefused')
            parsed = NarratedRecap.model_validate_json(message.content or '')
            # Schema compliance alone cannot ensure factuality, language or safe
            # content. Exact authored alternatives enforce all three at publication.
            if any(value not in options[key] for key, value in parsed.model_dump().items()):
                raise ValueError('UnapprovedCopy')
            episode = episode.model_copy(update={**parsed.model_dump(), 'narrated': True})
            audit['status'] = 'success'
        except Exception as exc:
            audit['status'] = 'fallback'
            audit['error_type'] = type(exc).__name__
            # Never log provider exception messages, response bodies or prompts.
        audit['latency_ms'] = int((time.monotonic() - started) * 1000)
        logger.info('narrator_run %s', json.dumps({'tick': episode.tick, **audit}))
        return episode, audit
