from glasshouse.live.schemas import Episode, Goal

NAMES = {
    "ru": {"dan": "Дэн", "max": "Макс", "eva": "Ева", "lea": "Лея"},
    "en": {"dan": "Dan", "max": "Max", "eva": "Eva", "lea": "Lea"},
}
TITLES = {
    "ru": [
        "Время поговорить",
        "Приглашение на свидание",
        "Возможность раскрыть секрет",
        "Обсудить разногласия",
        "Шанс помириться",
    ],
    "en": [
        "Time to talk",
        "An invitation to a date",
        "An opportunity to share a secret",
        "Talk through a disagreement",
        "A chance to reconcile",
    ],
}
CATEGORIES = ["conversation", "romance_opportunity", "reveal_secret", "conflict", "reconciliation"]
OUTCOMES = {
    "ru": {
        "conversation": (
            "Разговор, который сближает",
            "{pair} поговорили о жизни на вилле.",
            "Общий разговор укрепил доверие и симпатию.",
        ),
        "date": (
            "Время для двоих",
            "{pair} оба приняли приглашение и провели время на свидании.",
            "Взаимный выбор укрепил доверие. Продолжение зависит от самих участников.",
        ),
        "refusal": (
            "Возможность остаётся выбором",
            "{pair}: предложенная встреча не состоялась.",
            "Отказ или недоступность — полноценный исход. Голос не заменяет согласие.",
        ),
        "revelation": (
            "Один секрет стал общим",
            "Макс признался: долг Дэну ещё не возвращён.",
            "Теперь участники могут обсудить этот факт открыто.",
        ),
        "disagreement": (
            "Между ними — разногласие",
            "{pair} поспорили о доверии и жизни вместе.",
            "Напряжение выросло, доверие снизилось. Примирение потребует нового шага.",
        ),
        "reconciliation": (
            "Первый шаг навстречу",
            "{pair} выслушали друг друга и решили помириться.",
            "Доверие выросло, обида ослабла. Этот шаг ещё не решает всё.",
        ),
        "rest": (
            "Пауза тоже часть истории",
            "{pair} отложили разговор, чтобы отдохнуть.",
            "Усталость отложила развитие отношений. Участникам нужно время.",
        ),
    },
    "en": {
        "conversation": (
            "A conversation brings them closer",
            "{pair} talked about life at the villa.",
            "Their conversation strengthened trust and affinity.",
        ),
        "date": (
            "Time for two",
            "{pair} both accepted the invitation and spent time on a date.",
            "A mutual choice strengthened trust. What follows is up to the participants.",
        ),
        "refusal": (
            "An opportunity is still a choice",
            "{pair}: the proposed meeting did not happen.",
            "Refusal or unavailability is a complete outcome. A vote never replaces consent.",
        ),
        "revelation": (
            "One secret is now shared",
            "Max admitted that he has not repaid Dan yet.",
            "The participants can now discuss this fact openly.",
        ),
        "disagreement": (
            "A disagreement between them",
            "{pair} disagreed about trust and living together.",
            "Tension rose and trust fell. Reconciliation will take another step.",
        ),
        "reconciliation": (
            "A first step towards each other",
            "{pair} listened and chose to reconcile.",
            "Trust increased and resentment eased. One step does not resolve everything.",
        ),
        "rest": (
            "A pause is part of the story",
            "{pair} postponed their conversation to rest.",
            "Fatigue delayed the relationship story. The participants need time.",
        ),
    },
}
STRINGS = {
    "ru": {
        "show": "Эфир",
        "history": "Архив",
        "account": "Профиль",
        "login": "Войти",
        "register": "Создать аккаунт",
        "logout": "Выйти",
        "live": "ПРЯМО СЕЙЧАС",
        "villa": "Вилла",
        "season": "СЕЗОН 01",
        "headline": "У каждого выбора есть продолжение.",
        "intro": "Четыре AI-персонажа. Один общий дом. История, которая продолжается без вас — "
        "и может измениться с вашим участием.",
        "watch": "Смотреть эфир",
        "next": "До следующей серии",
        "episode": "Серия",
        "cast": "Жители виллы",
        "recap": "В предыдущей серии",
        "why": "Почему это важно",
        "goals": "Что предложим участникам?",
        "rules": "Голос открывает возможность. "
        "Участники сами решают, как поступить, и могут отказаться.",
        "remaining": "Бесплатного влияния осталось",
        "vote": "Поддержать",
        "points": "Очки",
        "votes": "влияния",
        "guest": "Войдите, чтобы получить 3 бесплатных очка на каждую серию.",
        "empty": "Вилла просыпается. Первая серия уже скоро.",
        "timeline": "Последние события",
        "email": "Email",
        "name": "Имя для профиля",
        "password": "Пароль (12–128 символов)",
        "locale": "Язык",
        "save": "Сохранить",
        "my_votes": "Ваши последние голоса",
        "no_votes": "Пока нет голосов. Первая возможность ждёт вас в эфире.",
        "previous": "Назад",
        "more": "Далее",
        "tick": "Запустить серию · Development",
        "loading": "Обновляем эфир…",
        "offline": "Связь прервалась. Попробуйте ещё раз.",
        "saved": "Сохранено",
        "voted": "Голос принят. Следующая серия покажет результат.",
        "footer": "AI-реалити • Бесплатное влияние • Без ставок и платежей",
        "teaser": "Как изменится разговор в следующей серии? Выберите новую возможность.",
        "back": "Вернуться в эфир",
        "exhausted": "Влияние на эту серию использовано.",
        "privacy": "Имя видно только вам. Ваши данные не отправляются рассказчику.",
        "starting": "Серия готовится…",
    },
    "en": {
        "show": "Live",
        "history": "Archive",
        "account": "Account",
        "login": "Log in",
        "register": "Create account",
        "logout": "Log out",
        "live": "LIVE NOW",
        "villa": "The Villa",
        "season": "SEASON 01",
        "headline": "Every choice has a next chapter.",
        "intro": "Four AI characters. One shared home. A story that continues while you are away — "
        "and can change when you take part.",
        "watch": "Watch live",
        "next": "Next episode in",
        "episode": "Episode",
        "cast": "Meet the house",
        "recap": "Previously at the villa",
        "why": "Why it matters",
        "goals": "What opportunity comes next?",
        "rules": "A vote opens an opportunity. "
        "Participants choose how to respond and can always refuse.",
        "remaining": "Free influence remaining",
        "vote": "Support",
        "points": "Points",
        "votes": "influence",
        "guest": "Log in for 3 free influence points every episode.",
        "empty": "The villa is waking up. The first episode is coming soon.",
        "timeline": "Recent moments",
        "email": "Email",
        "name": "Profile name",
        "password": "Password (12–128 characters)",
        "locale": "Language",
        "save": "Save",
        "my_votes": "Your recent votes",
        "no_votes": "No votes yet. Your first opportunity is live.",
        "previous": "Previous",
        "more": "Next",
        "tick": "Run episode · Development",
        "loading": "Updating the show…",
        "offline": "Connection interrupted. Please try again.",
        "saved": "Saved",
        "voted": "Vote accepted. The next episode will reveal the outcome.",
        "footer": "AI reality show • Free influence • No betting or payments",
        "teaser": "What will the next conversation bring? Choose a new opportunity.",
        "back": "Back to the show",
        "exhausted": "All influence for this episode has been used.",
        "privacy": "Only you see your profile name. Your details never reach the narrator.",
        "starting": "The episode is getting ready…",
    },
}
ERRORS = {
    "invalid": ("Проверьте поля формы.", "Please check the form fields."),
    "credentials": ("Неверный email или пароль.", "Incorrect email or password."),
    "registered": ("Не удалось создать аккаунт с этими данными.", "Could not create this account."),
    "auth": ("Войдите, чтобы продолжить.", "Please log in to continue."),
    "csrf": ("Форма устарела. Обновите страницу.", "This form expired. Please refresh the page."),
    "conflict": (
        "Эфир обновился. Обновите страницу и попробуйте снова.",
        "The show changed. Refresh and try again.",
    ),
    "budget": ("Лимит влияния на эту серию исчерпан.", "No influence remains for this episode."),
    "missing": ("Цель или сезон не найдены.", "Goal or season not found."),
    "rate": (
        "Слишком много попыток. Попробуйте через несколько минут.",
        "Too many attempts. Please try again in a few minutes.",
    ),
    "unavailable": (
        "Сервис временно недоступен. Попробуйте позже.",
        "The service is temporarily unavailable. Please try again later.",
    ),
}
STATUS = {
    "ru": {
        "kitchen": "Кухня",
        "living_room": "Гостиная",
        "bedroom_a": "Спальня A",
        "bedroom_b": "Спальня B",
        "garden": "Сад",
        "terrace": "Терраса",
        "bathroom": "Ванная",
        "idle": "Отдыхает",
        "sitting": "Отдыхает",
        "walking": "В пути",
        "sleeping": "Спит",
        "eating": "За столом",
        "cooking": "Готовит",
        "conversing": "Беседует",
        "thoughtful": "В раздумьях",
        "neutral": "Спокойствие",
        "calm": "Спокойствие",
    },
    "en": {
        "kitchen": "Kitchen",
        "living_room": "Living room",
        "bedroom_a": "Bedroom A",
        "bedroom_b": "Bedroom B",
        "garden": "Garden",
        "terrace": "Terrace",
        "bathroom": "Bathroom",
        "idle": "Resting",
        "sitting": "Resting",
        "walking": "Walking",
        "sleeping": "Sleeping",
        "eating": "Eating",
        "cooking": "Cooking",
        "conversing": "Talking",
        "thoughtful": "Thoughtful",
        "neutral": "Calm",
        "calm": "Calm",
    },
}


def goal_view(goal, locale):
    names = NAMES[locale]
    pair = (" и " if locale == "ru" else " and ").join(names[x] for x in goal.eligible_characters)
    return Goal(
        id=goal.id,
        title=TITLES[locale][CATEGORIES.index(goal.category.value)],
        description=pair + ". " + STRINGS[locale]["rules"],
        category=goal.category.value,
        status=goal.status.value,
        tick=goal.tick,
        votes=goal.votes,
        eligible_characters=goal.eligible_characters,
        locale=locale,
    )


def episode_view(engine, locale):
    recap = engine.show.recaps[-1]
    goal = next((g for g in engine.show.goals if g.id == recap.story_goal_id), None)
    participants = goal.eligible_characters if goal else ()
    outcome = goal.result.outcome if goal and goal.result else "rest"
    pair = (" и " if locale == "ru" else " and ").join(NAMES[locale][x] for x in participants)
    headline, happened, why = OUTCOMES[locale][outcome]
    return Episode(
        headline=headline,
        what_happened=happened.format(pair=pair),
        why_it_matters=why,
        teaser=STRINGS[locale]["teaser"],
        tick=recap.tick,
        locale=locale,
        outcome=outcome,
        participants=participants,
        relationship_changes=[c.model_dump() for c in recap.relationship_changes],
        sim_time=recap.sim_time,
        story_goal_id=recap.story_goal_id,
    )


def editorial_options(episode):
    """Bound narration to authored factual copy; no generated claims can reach viewers."""
    ru = episode.locale == "ru"
    return {
        "headline": [
            episode.headline,
            ("На вилле: " if ru else "At the villa: ") + episode.headline,
        ],
        "what_happened": [
            episode.what_happened,
            ("В этой серии: " if ru else "This episode: ") + episode.what_happened,
        ],
        "why_it_matters": [episode.why_it_matters],
        "teaser": [
            episode.teaser,
            "Следующий шаг — новая возможность. Как ответят участники?"
            if ru
            else "A new opportunity is next. How will the participants respond?",
        ],
    }
