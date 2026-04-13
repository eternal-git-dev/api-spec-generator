import re
import numpy as np
from numpy.linalg import norm
from gensim.models import Word2Vec
import pymorphy3


# ДАННЫЕ


REFERENCE_DOCSTRINGS = {
    "group_prefixes": "Возвращает список префиксов всех доступных групп.",
    "group":          "Возвращает список групп с их идентификатором и названием по заданному префиксу.",
    "variant_list":   "Возвращает список идентификаторов всех вариантов из базы данных.",
    "task_list":      "Возвращает список задач с их статусами для заданной группы и варианта.",
    "task":           "Возвращает статус конкретной задачи по идентификаторам группы, варианта и задачи.",
    "submit_task":    "Отправляет код решения задачи, проверяет токен авторизации и возвращает обновлённый статус.",
}


GENERATED_DOCSTRINGS = {
    "group_prefixes": (
        "Возвращает список всех доступных префиксов групп. "
        "Вызывает groups.get_groupings() для получения всех группировок, "
        "извлекает их ключи и возвращает их в виде JSON-объекта по ключу prefixes."
    ),
    "group": (
        "Получает группы, соответствующие указанному префиксу. "
        "Выполняет поиск групп с заданным префиксом в базе данных, формирует список "
        "словарей, содержащих id и title, и возвращает этот список в формате JSON."
    ),
    "variant_list": (
        "Список всех вариантов. "
        "Возвращает список идентификаторов всех вариантов. Параметров не требуется."
    ),
    "task_list": (
        "Получение списка задач по группе и варианту. "
        "Возвращает задачи, отфильтрованные указанным идентификатором группы и варианта. "
        "Параметры gid и vid должны быть целыми числами."
    ),
    "task": (
        "Получение статуса задачи. "
        "Возвращает текущий статус задачи, определённый идентификаторами группы, "
        "варианта и задачи. Принимает параметры gid, vid, tid."
    ),
    "submit_task": (
        "Отправка ответа на задачу. "
        "Проверяет токен авторизации и изменяет статус задачи, "
        "принимая код ответа из тела запроса."
    ),
}

# Метаданные для шаблонного генератора
METHOD_META = {
    "group_prefixes": {"params": [],                               "return_type": "список"},
    "group":          {"params": ["prefix"],                       "return_type": "список"},
    "variant_list":   {"params": [],                               "return_type": "список"},
    "task_list":      {"params": ["gid", "vid"],                   "return_type": "список"},
    "task":           {"params": ["gid", "vid", "tid"],            "return_type": "объект"},
    "submit_task":    {"params": ["gid", "vid", "tid", "code", "token"], "return_type": "объект"},
}

def make_template(name: str, meta: dict) -> str:
    params = ", ".join(meta["params"]) if meta["params"] else "отсутствуют"
    return f"Метод {name} с параметрами {params} возвращает значение типа {meta['return_type']}."

TEMPLATE_DOCSTRINGS = {k: make_template(k, v) for k, v in METHOD_META.items()}


# ПРЕДОБРАБОТКА


morph = pymorphy3.MorphAnalyzer()

POS_MAP = {
    'NOUN': 'NOUN', 'VERB': 'VERB', 'INFN': 'VERB',
    'ADJF': 'ADJ',  'ADJS': 'ADJ',  'ADVB': 'ADV',
    'PRTF': 'ADJ',  'PRTS': 'ADJ',  'GRND': 'VERB',
    'NUMR': 'NUM',  'NPRO': 'PRON', 'PREP': 'ADP',
    'CONJ': 'CCONJ','PRCL': 'PART', 'INTJ': 'INTJ',
}

def preprocess(text: str) -> list:
    tokens = re.findall(r'[а-яёa-z]+', text.lower())
    result = []
    for tok in tokens:
        if len(tok) <= 1:
            continue
        p = morph.parse(tok)[0]
        upos = POS_MAP.get(p.tag.POS, 'X')
        result.append(f"{p.normal_form}_{upos}")
    return result


# БУЧЕНИЕ Word2Vec  (общий корпус: эталон + LLM + шаблон)


all_texts = (list(REFERENCE_DOCSTRINGS.values()) +
             list(GENERATED_DOCSTRINGS.values()) +
             list(TEMPLATE_DOCSTRINGS.values()))

corpus = [preprocess(t) for t in all_texts]

# eed фиксирован, а значит воспроизводимые результаты
model = Word2Vec(
    sentences=corpus,
    vector_size=100,
    window=5,
    min_count=1,
    workers=1,       # workers=1 обязателен при фиксированном seed
    epochs=500,
    sg=0,
    seed=42,
)

#  ВЕКТОРИЗАЦИЯ И СХОДСТВО

def doc_vec(tokens: list) -> np.ndarray:
    vecs = [model.wv[t] for t in tokens if t in model.wv]
    return np.mean(vecs, axis=0) if vecs else np.zeros(model.vector_size)

def cosine(u: np.ndarray, v: np.ndarray) -> float:
    n = norm(u) * norm(v)
    return float(np.dot(u, v) / n) if n > 0 else 0.0


# ВЫВОД: токены + таблица результатов


print("=" * 72)
print("  ТОКЕНЫ ПОСЛЕ ЛЕММАТИЗАЦИИ")
print("=" * 72)
for name, text in TEMPLATE_DOCSTRINGS.items():
    print(f"\n[{name}]")
    print(f"  Шаблон : {text}")
    print(f"  Токены : {preprocess(text)}")

print("\n" + "=" * 72)
print(f"  {'Метод':<20} | {'Эталон (токены)'}")
print("=" * 72)
for name, text in REFERENCE_DOCSTRINGS.items():
    print(f"  {name:<20} | {preprocess(text)}")

print("\n" + "=" * 72)
print(f"  {'Метод':<20} | {'sim LLM':>9} | {'sim Шаблон':>10} | {'Δ':>7}")
print("=" * 72)

llm_scores, tmpl_scores = {}, {}
for name in REFERENCE_DOCSTRINGS:
    rv  = doc_vec(preprocess(REFERENCE_DOCSTRINGS[name]))
    lv  = doc_vec(preprocess(GENERATED_DOCSTRINGS[name]))
    tv  = doc_vec(preprocess(TEMPLATE_DOCSTRINGS[name]))
    ls  = cosine(rv, lv)
    ts  = cosine(rv, tv)
    llm_scores[name]  = ls
    tmpl_scores[name] = ts
    print(f"  {name:<20} | {ls:>9.4f} | {ts:>10.4f} | {ls - ts:>+7.4f}")

avg_l = sum(llm_scores.values())  / len(llm_scores)
avg_t = sum(tmpl_scores.values()) / len(tmpl_scores)
print("=" * 72)
print(f"  {'Среднее':<20} | {avg_l:>9.4f} | {avg_t:>10.4f} | {avg_l - avg_t:>+7.4f}")
print("=" * 72)
print(f"\n  Преимущество LLM над шаблоном: {avg_l - avg_t:.4f}")
