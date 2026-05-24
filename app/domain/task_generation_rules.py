import random


def make_options(correct: int | float, difficulty: int) -> list[str]:
    spread = max(3, difficulty * 2)
    values = {correct}
    while len(values) < 4:
        values.add(correct + random.choice([-1, 1]) * random.randint(1, spread))
    return [str(v) for v in random.sample(list(values), 4)]
